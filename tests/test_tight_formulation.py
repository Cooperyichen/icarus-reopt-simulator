import sys
import os
import unittest


class TestTightMinMaxLinkUtilizationFormulation(unittest.TestCase):
    def test_tight_formulation_output_shape_and_attrs(self):
        """
        T1 gate: when optimization.use_tight_formulation=true, optimizer output shape
        (DataFrame columns) and attrs keys should be compatible with existing pipeline.
        """
        # Add the project src directory to the Python path (match other tests)
        project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(project_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Local imports to avoid altering global import order for other tests
        from topo.utils import load_yaml_file
        from topo.toroidal_topo import ToroidalTopo
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer

        cfg_path = os.path.join(project_path, "tests", "fixtures", "test_tight_formulation_2c.yaml")
        config = load_yaml_file(cfg_path)

        width = config["system"]["width"]
        height = config["system"]["height"]
        topo = ToroidalTopo(scenario_config=config, width=width, height=height)

        num_commodities = config["optimization"]["num_commodities"]
        demand_matrix = topo.generate_demand_matrix(num_commodities=num_commodities)

        optimizer = MultiCommodityOptimizer(config, topo.graph, topo.interlinks)
        objective_type = config["optimization"]["objective_func"]
        mode = config["simulation"]["failure_strategy"]

        result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)

        # Basic shape checks
        expected_cols = {"id_flow", "Source", "Destination", "Arrival Rate", "Path", "Priority"}
        self.assertTrue(expected_cols.issubset(set(result_df.columns)))

        # Attrs should exist for downstream analysis scripts
        self.assertTrue(hasattr(result_df, "attrs"))
        self.assertIn("dual_variables", result_df.attrs)
        self.assertIn("capacity_dual_variables", result_df.attrs)

    def test_tight_formulation_duals_available_and_signs(self):
        """
        T2 gate: demand duals should be available (non-None) with the expected sign,
        and the max-utilization edge should have a non-trivial tight-constraint dual (mu).
        """
        project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(project_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from topo.utils import load_yaml_file
        from topo.toroidal_topo import ToroidalTopo
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        from main.enhanced_dual_analysis import find_max_utilization_edge
        from main.analyze_all_dual_variables import match_edge_in_capacity_duals

        cfg_path = os.path.join(project_path, "tests", "fixtures", "test_tight_formulation_2c.yaml")
        config = load_yaml_file(cfg_path)

        topo = ToroidalTopo(scenario_config=config, width=config["system"]["width"], height=config["system"]["height"])
        demand_matrix = topo.generate_demand_matrix(num_commodities=config["optimization"]["num_commodities"])

        optimizer = MultiCommodityOptimizer(config, topo.graph, topo.interlinks)
        result_df = optimizer.solve_mcfp_path_formulation(
            demand_matrix,
            config["optimization"]["objective_func"],
            config["simulation"]["failure_strategy"],
        )

        demand_duals = result_df.attrs.get("dual_variables", {})
        self.assertIn(0, demand_duals)
        self.assertIn(1, demand_duals)
        self.assertIsNotNone(demand_duals[0])
        self.assertIsNotNone(demand_duals[1])
        # Expected sign convention: increasing demand should increase optimal z (positive dual)
        self.assertGreater(demand_duals[0], 0.0)
        self.assertGreater(demand_duals[1], 0.0)

        capacity_duals = result_df.attrs.get("capacity_dual_variables", {})
        self.assertTrue(len(capacity_duals) > 0)

        max_edge, _ = find_max_utilization_edge(result_df, config)
        matched_key, mu_e = match_edge_in_capacity_duals(max_edge, capacity_duals)
        self.assertIsNotNone(matched_key)
        self.assertIsNotNone(mu_e)
        self.assertGreater(mu_e, 1e-10)

    def test_tight_formulation_matches_legacy_objective_value(self):
        """
        T3 gate: tight epigraph formulation should match legacy min-max objective
        value (max link utilization %) within a small tolerance.
        """
        project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        src_path = os.path.join(project_path, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from topo.utils import load_yaml_file
        from topo.toroidal_topo import ToroidalTopo
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        from main.multi_step_comparison_experiment import calculate_max_link_utilization

        cfg_path = os.path.join(project_path, "tests", "fixtures", "test_tight_formulation_2c.yaml")
        base_config = load_yaml_file(cfg_path)

        def run_and_measure(config_dict):
            topo = ToroidalTopo(
                scenario_config=config_dict,
                width=config_dict["system"]["width"],
                height=config_dict["system"]["height"],
            )
            demand_matrix = topo.generate_demand_matrix(num_commodities=config_dict["optimization"]["num_commodities"])
            optimizer = MultiCommodityOptimizer(config_dict, topo.graph, topo.interlinks)
            df = optimizer.solve_mcfp_path_formulation(
                demand_matrix,
                config_dict["optimization"]["objective_func"],
                config_dict["simulation"]["failure_strategy"],
            )
            return calculate_max_link_utilization(df, config_dict)

        # Legacy (use_tight_formulation = false)
        legacy_config = dict(base_config)
        legacy_config["optimization"] = dict(base_config["optimization"])
        legacy_config["optimization"]["use_tight_formulation"] = False
        legacy_util = run_and_measure(legacy_config)

        # Tight (use_tight_formulation = true)
        tight_config = dict(base_config)
        tight_config["optimization"] = dict(base_config["optimization"])
        tight_config["optimization"]["use_tight_formulation"] = True
        tight_util = run_and_measure(tight_config)

        # SCS numerical tolerance can introduce small discrepancies between two equivalent forms.
        self.assertAlmostEqual(legacy_util, tight_util, delta=1e-1)


if __name__ == "__main__":
    unittest.main()

