"""Simple mGear post script launcher with step dictionary support
Maya: 2022.2 • Deps: cmds, mgear
"""

import json
import os
import maya.cmds as cmds
import mgear.shifter.custom_step as cstp
import importlib.util
import inspect


def launch_post_with_steps(post_script_path, step_dict_path=None):
    """Launch mGear post script with custom step dictionary.

    Args:
        post_script_path (str): Full path to the post script file
        step_dict_path (str, optional): Path to step dictionary JSON
    """
    if step_dict_path is None:
        workspace = cmds.workspace(q=True, rd=True)
        step_dict_path = os.path.join(workspace, "data", "stepDict.json")

    # Load step dictionary
    with open(step_dict_path, 'r') as f:
        data = json.load(f)

    mgear_data = data["mgearRun"]

    # Component class
    class Component:
        def __init__(self, comp_data):
            self.name = comp_data.get("name", "")
            self.side = comp_data.get("side", "")
            self.index = comp_data.get("index", 0)
            self.count = comp_data.get("count", 0)

            self.uihost = comp_data.get("uihost")
            self.settings = comp_data.get("settings", {})
            self.build_data = comp_data.get("build_data", {})

            self.groups = {}
            groups_data = comp_data.get("groups", {})

            for grp_key, grp_value in groups_data.items():
                if grp_value is None:
                    self.groups[grp_key] = None
                elif isinstance(grp_value, list):
                    self.groups[grp_key] = grp_value
                else:
                    self.groups[grp_key] = grp_value

            self.controlers = self.groups.get("controllers", [])
            self.jointList = self.groups.get("deformers", [])

            roots = self.groups.get("componentsRoots", [])
            self.root = roots[0] if roots else None

            self.fk_npo = comp_data.get("fk_npo", [])

    # MgearRun class
    class MgearRun:
        def __init__(self, mgear_data):
            self.model = mgear_data.get("model")

            self.components = {}
            for key, comp_data in mgear_data.get("components", {}).items():
                self.components[key] = Component(comp_data)

    # Create stepDict
    mgear_run_obj = MgearRun(mgear_data)
    stepDict = {"mgearRun": mgear_run_obj}

    # Load post script module
    spec = importlib.util.spec_from_file_location("post_script", post_script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find and run CustomShifterStep class
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, cstp.customShifterMainStep):
            if obj != cstp.customShifterMainStep:
                print(f"Found custom step class: {name}")

                # Check __init__ signature
                sig = inspect.signature(obj.__init__)
                params = list(sig.parameters.keys())
                print(f"__init__ parameters: {params}")

                # Instantiate based on signature
                if 'stored_dict' in params:
                    instance = obj(stepDict)
                    print(f"Instantiated with stepDict")
                elif len(params) == 1:  # Just 'self'
                    instance = obj()
                    instance._stored_dict = stepDict
                    print(f"Instantiated without arguments, injected _stored_dict")
                else:
                    instance = obj(stepDict)
                    print(f"Instantiated with stepDict (default)")

                step_name = getattr(instance, 'name', 'unnamed_step')
                print(f"Running: {step_name}")

                # Check run signature
                try:
                    run_sig = inspect.signature(instance.run)
                    run_params = list(run_sig.parameters.keys())
                except:
                    run_params = ['self']  # Default if inspection fails

                print(f"run() parameters: {run_params}")

                # Run based on signature
                if len(run_params) <= 1:  # Just 'self' or empty
                    instance.run()
                else:  # Has additional parameters
                    instance.run(stepDict)

                print(f"Completed: {step_name}")
                break


# Example usage
if __name__ == "__main__":
    launch_post_with_steps(
        post_script_path=r"c:\scripts\mgear_post\my_post_script.py",
        step_dict_path=None
    )