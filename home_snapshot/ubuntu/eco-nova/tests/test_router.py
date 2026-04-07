import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eco_nova.architecture import WorkflowArchitecture, ClusterArchitecture
from eco_nova.router import route_message


def build_architecture() -> WorkflowArchitecture:
    return WorkflowArchitecture(
        workflows_dir="/tmp",
        entry_workflows=[],
        main_orchestrator="orq",
        output_engine="out",
        ext_workflows=[],
        clusters={
            "sistema": ClusterArchitecture(
                cluster_id="sistema",
                workflow_name="Sistema",
                file_path="",
                prompt_excerpt="",
                subagents=[
                    "XUS Flow v1.0 | N8N",
                    "XUS Drive v1.0 - Docs & Files",
                ],
            ),
            "negocio": ClusterArchitecture(
                cluster_id="negocio",
                workflow_name="Negocio",
                file_path="",
                prompt_excerpt="",
                subagents=[
                    "XUS Hunter v1.0 - Lead Intelligence",
                    "Xus Outreach Engine - V1.0",
                ],
            ),
            "vida": ClusterArchitecture(
                cluster_id="vida",
                workflow_name="Vida",
                file_path="",
                prompt_excerpt="",
                subagents=["XUS Habits v2.0 - Dual Agent"],
            ),
            "multimedia": ClusterArchitecture(
                cluster_id="multimedia",
                workflow_name="Multimedia",
                file_path="",
                prompt_excerpt="",
                subagents=["XUS DJ v10 - Optimized Single Agent"],
            ),
        },
    )


class RouterTests(unittest.TestCase):
    def test_routes_business_message(self) -> None:
        architecture = build_architecture()
        result = route_message("busca leads y prepara outreach para coaches", architecture)
        self.assertEqual(result.cluster_id, "negocio")
        self.assertTrue(result.selected_subagents)

    def test_routes_life_message(self) -> None:
        architecture = build_architecture()
        result = route_message("listo push ups y agenda una reunion manana", architecture)
        self.assertEqual(result.cluster_id, "vida")

    def test_defaults_to_system(self) -> None:
        architecture = build_architecture()
        result = route_message("hola", architecture)
        self.assertEqual(result.cluster_id, "sistema")


if __name__ == "__main__":
    unittest.main()
