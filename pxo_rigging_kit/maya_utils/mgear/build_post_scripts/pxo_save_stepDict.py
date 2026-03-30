import json
import os
import mgear.shifter.custom_step as cstp
import pymel.core as pm


class CustomShifterStep(cstp.customShifterMainStep):
    """mGear custom step to save comprehensive component data to JSON.

    Captures mgearRun model, components with groups/settings/controllers,
    rigGroups, and additional build data for complete rig documentation.
    Outputs to workspace/data/stepDict_complete.json
    """

    def setup(self):
        """Setup step name"""
        self.name = "save_stepdict"

    def run(self):
        """Save comprehensive component data"""
        json_path = os.path.join(
            pm.workspace(q=True, rd=True),
            "data",
            "stepDict.json"
        )

        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        mgear_run = self.mgear_run
        data = {
            "mgearRun": {
                "model": str(mgear_run.model),
                "components": {},
                "rigGroups": {}
            }
        }

        if hasattr(mgear_run.model, 'rigGroups'):
            try:
                rig_groups = mgear_run.model.rigGroups.inputs()
                data["mgearRun"]["rigGroups"] = {
                    "rig_sets": str(rig_groups[0]) if len(rig_groups) > 0 else None,
                    "controllers_sets": str(rig_groups[1]) if len(rig_groups) > 1 else None,
                    "componentsRoots_sets": str(rig_groups[2]) if len(rig_groups) > 2 else None,
                    "deformers_sets": str(rig_groups[3]) if len(rig_groups) > 3 else None
                }
            except:
                pass

        for comp_key, comp in mgear_run.components.items():
            comp_data = {
                "name": comp.name,
                "side": comp.side,
                "index": comp.index,
                "count": getattr(comp, 'count', 0),
                "groups": {},
                "settings": {},
                "uihost": None,
                "fk_npo": [],
                "build_data": {}
            }

            if hasattr(comp, 'uihost') and comp.uihost:
                comp_data["uihost"] = str(comp.uihost)

            if hasattr(comp, 'settings'):
                for key, value in comp.settings.items():
                    if hasattr(value, '__str__'):
                        comp_data["settings"][key] = str(value)
                    else:
                        comp_data["settings"][key] = value

            if hasattr(comp, 'groups') and comp.groups:
                for grp_key, grp_value in comp.groups.items():
                    if isinstance(grp_value, list):
                        comp_data["groups"][grp_key] = [str(item) for item in grp_value]
                    elif grp_value is not None:
                        comp_data["groups"][grp_key] = str(grp_value)
                    else:
                        comp_data["groups"][grp_key] = None

            if not comp_data["groups"].get("controllers"):
                if hasattr(comp, 'controlers'):
                    comp_data["groups"]["controllers"] = [str(c) for c in comp.controlers]

            if not comp_data["groups"].get("deformers"):
                if hasattr(comp, 'jointList'):
                    comp_data["groups"]["deformers"] = [str(j) for j in comp.jointList]

            if not comp_data["groups"].get("componentsRoots"):
                if hasattr(comp, 'root'):
                    comp_data["groups"]["componentsRoots"] = [str(comp.root)]

            if hasattr(comp, 'fk_npo'):
                if isinstance(comp.fk_npo, list):
                    comp_data["fk_npo"] = [str(n) for n in comp.fk_npo]
                elif comp.fk_npo:
                    comp_data["fk_npo"] = [str(comp.fk_npo)]

            if hasattr(comp, 'build_data'):
                comp_data["build_data"] = dict(comp.build_data)

            data["mgearRun"]["components"][comp_key] = comp_data

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Complete stepDict saved to: {json_path}")
        print(f"Saved {len(data['mgearRun']['components'])} components with full data")

        return