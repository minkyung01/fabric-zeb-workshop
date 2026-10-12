import copy
import json
import sys
import threading
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from reference import (SCENARIO, baseline, candidates,
                       decision_record, digest, fixtures, grade, guard_target, idempotent,
                       purchase_status, validate)
from fetch_public import parse_csv

SOURCE_WORKSPACE = str(uuid.UUID(int=1000))
SOURCE_LAKEHOUSE = str(uuid.UUID(int=1001))


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = fixtures()
        cls.criteria = cls.data["ref_zeb_grade_criteria"]["rows"]
        cls.status = baseline(cls.data)
        cls.options = candidates(cls.data)

    def config(self):
        return {"participant_id": "p01", "scenario_id": SCENARIO,
                "workspace_id": str(uuid.UUID(int=1)), "lakehouse_id": str(uuid.UUID(int=2)),
                "protected_workspace_ids": [SOURCE_WORKSPACE], "protected_lakehouse_ids": [SOURCE_LAKEHOUSE],
                "approved_target": True, "platform_approval_binding_verified": True,
                "configured_creator_actor_id": str(uuid.UUID(int=4)),
                "action_binding_evidence_ref": "LOCAL_TEST_BINDING_NOT_REAL_APPROVAL"}

    def request(self, option="OPT-D5+OPT-D6"):
        r = next(r for r in self.options if r["option_set_id"] == option)
        return {"participant_id": "p01", "scenario_id": SCENARIO,
                "site_code": "HS-D", "option_set_id": option, "event_id": r["event_id"],
                "baseline_hash": r["baseline_hash"], "result_hash": digest(r),
                "decision": "record_for_engineering_review",
                "approval_evidence_ref": "LOCAL_TEST_EXTERNAL_REFERENCE_NOT_LIVE_APPROVAL"}

    def test_source_counts_and_unicode(self):
        expected = [6, 17, 8, 8, 8, 8, 18, 12, 10, 48, 39, 9, 25, 1, 12, 0]
        self.assertEqual([len(t["rows"]) for t in self.data.values()], expected)
        self.assertEqual(self.data["pms_site"]["rows"][0]["stage"], "시공")

    def test_fixture_keys_valid(self):
        self.assertTrue(validate(self.data))

    def test_duplicate_rejected(self):
        data = copy.deepcopy(self.data)
        data["pms_site"]["rows"].append(data["pms_site"]["rows"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate/null"):
            validate(data)

    def test_orphan_rejected(self):
        data = copy.deepcopy(self.data)
        data["scm_purchase_order"]["rows"][0]["wbs_element"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "Orphan"):
            validate(data)

    def test_wrong_site_certificate_rejected(self):
        data = copy.deepcopy(self.data)
        data["pms_certificate"]["rows"][0]["design_version_id"] = "BIM-0397-V2"
        with self.assertRaisesRegex(ValueError, "another site's"):
            validate(data)

    def test_current_design_unique(self):
        data = copy.deepcopy(self.data)
        next(r for r in data["bim_design_version"]["rows"]
             if r["version_id"] == "BIM-0397-V2")["version_status"] = "현행"
        with self.assertRaisesRegex(ValueError, "exactly one"):
            validate(data)

    def test_or_counterexample(self):
        self.assertEqual(grade(39, 65, True, self.criteria), 4)

    def test_strict_pe_and_inclusive_ss(self):
        self.assertEqual(grade(39, 70, True, self.criteria), 5)
        self.assertEqual(grade(40, 70, True, self.criteria), 4)
        self.assertEqual(grade(0, 69.999, True, self.criteria), 4)

    def test_rank_plus_failure_nonresidential(self):
        self.assertEqual(grade(120, 999, True, self.criteria), 0)
        self.assertEqual(grade(0, 130, False, self.criteria), 6)
        self.assertEqual(grade(39, 89, False, self.criteria), 4)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            grade("NaN", 1, True, self.criteria)

    def test_baseline_and_submitted_version(self):
        d = next(r for r in self.status if r["site_code"] == "HS-D")
        self.assertEqual((d["current_version_id"], d["submitted_version_id"]),
                         ("BIM-0397-V3", "BIM-0397-V2"))
        self.assertEqual((d["selfsuff_pct"], d["primary_energy_kwh_m2y"], d["grade_rank"]),
                         (38.2, 76, 5))
        self.assertEqual(sum(r["risk"] != "normal" for r in self.status), 4)
        self.assertEqual({r["site_code"]: r["grade_rank"] for r in self.status},
                         {"HS-A": 4, "IC-B": 4, "SN-C": 3, "HS-D": 5,
                          "SJ-E": 3, "BS-F": 2, "JJ-G": 3, "MP-H": 5})

    def test_sixty_three_and_minimum(self):
        self.assertEqual(len(self.options), 63)
        r = next(r for r in self.options if r["energy_feasible"])
        self.assertEqual((r["option_set_id"], r["selfsuff_pct"], r["primary_energy_kwh_m2y"],
                          r["cost_krw"], r["parallel_lead_days"]),
                         ("OPT-D5+OPT-D6", "40.1", "72.2", 110000000, 30))
        self.assertFalse(any(r["decision_feasible"] for r in self.options))

    def test_d1_pe70_passes_ss_only(self):
        d = next(r for r in self.options if r["option_set_id"] == "OPT-D1")
        self.assertEqual(d["primary_energy_kwh_m2y"], "70.0")
        self.assertEqual(d["grade_rank"], 4)

    def test_purchase_no_fake_shock(self):
        rows = purchase_status(self.data)
        self.assertEqual(len(rows), 25)
        self.assertFalse(any(r["deadline_breach"] for r in rows))
        d = next(r for r in rows if r["po_no"] == "4500031202")
        self.assertEqual((d["effective_eta"], d["installation_deadline"]), ("2026-11-12", "2026-11-30"))
        event = self.data["scm_po_event"]["rows"][0]
        self.assertEqual(next(r for r in rows if r["po_no"] == event["po_no"])["effective_eta"], "2027-04-20")

    def test_stable_event_hash(self):
        self.assertEqual(self.status, baseline(self.data))
        data = copy.deepcopy(self.data)
        next(r for r in data["bim_design_version"]["rows"]
             if r["version_id"] == "BIM-0397-V3")["selfsuff_pct"] = 38.3
        changed = next(r for r in baseline(data) if r["site_code"] == "HS-D")
        self.assertNotEqual(changed["event_id"], next(r for r in self.status if r["site_code"] == "HS-D")["event_id"])

    def test_guard_accepts_approved_matching(self):
        c = self.config()
        self.assertTrue(guard_target(c, c["workspace_id"], c["lakehouse_id"]))

    def test_guard_rejects_original(self):
        for key, source in (("workspace_id", SOURCE_WORKSPACE), ("lakehouse_id", SOURCE_LAKEHOUSE)):
            c = self.config()
            c[key] = source
            with self.assertRaises(ValueError):
                guard_target(c, c["workspace_id"], c["lakehouse_id"])

    def test_guard_requires_valid_protected_source_lists(self):
        for key in ("protected_workspace_ids", "protected_lakehouse_ids"):
            for value in (None, [], "not-a-list", [None], ["CHANGE_ME"], [str(uuid.UUID(int=0))]):
                c = self.config()
                c[key] = value
                with self.assertRaises(ValueError):
                    guard_target(c, c["workspace_id"], c["lakehouse_id"])

    def test_guard_rejects_placeholders_mismatch_unapproved(self):
        for update in ({"workspace_id": None}, {"lakehouse_id": "CHANGE_ME"}, {"approved_target": False},
                       {"participant_id": "p13"}, {"scenario_id": "other"},
                       {"lakehouse_id": str(uuid.UUID(int=0))}):
            c = self.config()
            c.update(update)
            with self.assertRaises((ValueError, TypeError)):
                guard_target(c, c["workspace_id"], c["lakehouse_id"])
        c = self.config()
        with self.assertRaises(ValueError):
            guard_target(c, str(uuid.UUID(int=3)), c["lakehouse_id"])

    def test_unapproved_and_physical_actions_rejected(self):
        for update in ({"human_approved": False}, {"human_approved": True}, {"approved_by": "spoofed"},
                       {"decision": "apply_options"}, {"identity_mode": "verified_teams_identity"},
                       {"approval_evidence_ref": "x" * 2049}):
            r = self.request()
            r.update(update)
            with self.assertRaises(ValueError):
                decision_record(r, self.config(), self.data)

    def test_action_binding_and_creator_required_not_client_flag(self):
        for update in ({"platform_approval_binding_verified": False}, {"action_binding_evidence_ref": ""},
                       {"configured_creator_actor_id": None}, {"configured_creator_actor_id": str(uuid.UUID(int=0))}):
            config = self.config()
            config.update(update)
            with self.assertRaises(ValueError):
                decision_record(self.request(), config, self.data)

    def test_provenance_does_not_invent_human_identity(self):
        request = self.request()
        record = decision_record(request, self.config(), self.data)
        self.assertEqual(record["human_approver_identity"], "not_supplied_or_verified")
        self.assertEqual(record["approval_evidence_status"], "externally_supplied_not_verified")
        self.assertEqual(record["approval_evidence_ref"], request["approval_evidence_ref"])
        self.assertEqual(record["configured_creator_actor_id"], self.config()["configured_creator_actor_id"])
        self.assertEqual(record["execution_principal_verification"], "configured_creator_not_verified_in_notebook")
        request["approval_evidence_ref"] = ""
        self.assertEqual(decision_record(request, self.config(), self.data)["approval_evidence_status"], "not_supplied_by_platform")

    def test_decision_rejects_unapproved_original_target(self):
        for update in ({"approved_target": False}, {"workspace_id": SOURCE_WORKSPACE},
                       {"lakehouse_id": SOURCE_LAKEHOUSE}):
            config = self.config()
            config.update(update)
            with self.assertRaises(ValueError):
                decision_record(self.request(), config, self.data)

    def test_request_scope_stale_and_unknown_rejected(self):
        for update in ({"site_code": "MP-H"}, {"participant_id": "p02"}, {"scenario_id": "other"},
                       {"event_id": "stale"}, {"baseline_hash": "stale"}, {"result_hash": "stale"},
                       {"option_set_id": "OPT-H1"}, {"option_set_id": "__import__('os')"}):
            r = self.request()
            r.update(update)
            with self.assertRaises(ValueError):
                decision_record(r, self.config(), self.data)

    def test_infeasible_option_rejected(self):
        with self.assertRaises(ValueError):
            decision_record(self.request("OPT-D6"), self.config(), self.data)

    def test_duplicate_idempotent(self):
        r = decision_record(self.request(), self.config(), self.data)
        rows = idempotent([], r)
        self.assertEqual(idempotent(rows, r), rows)
        self.assertEqual(len(rows), 1)

    def test_conflicting_payload_preserved(self):
        first = decision_record(self.request(), self.config(), self.data)
        request = self.request()
        request["approval_evidence_ref"] = "DIFFERENT_EXTERNAL_REFERENCE"
        second = decision_record(request, self.config(), self.data)
        self.assertEqual(first["decision_id"], second["decision_id"])
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            idempotent([first], second)

    def test_confirmed_option_must_match_recommendation(self):
        with self.assertRaisesRegex(ValueError, "differs"):
            decision_record(self.request("OPT-D2"), self.config(), self.data)

    def test_serialized_local_writers_only(self):
        # A lock models the REQUIRED serialized writer, not distributed Delta isolation.
        lock = threading.Lock()
        rows = []
        record = decision_record(self.request(), self.config(), self.data)
        def write():
            nonlocal rows
            with lock:
                rows = idempotent(rows, record)
        threads = [threading.Thread(target=write) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(rows), 1)

    def test_reference_answer_parity(self):
        path = Path(__file__).resolve().parents[1] / "data" / "reference_answers.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved, {"baseline": self.status, "hs_d_options": self.options,
                                "po_status": purchase_status(self.data)})

    def test_public_html_and_small_files_rejected(self):
        for raw in (b"<html>captcha</html>", b" a,b\n1,2\n", b'{"status": false}', b""):
            with self.assertRaises(ValueError):
                parse_csv(raw, [])


if __name__ == "__main__":
    unittest.main()
