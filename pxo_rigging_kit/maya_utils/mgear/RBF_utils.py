import json
import maya.cmds as cmds
import pymel.core as pmc

from mgear.rigbits.weightNode_io import RBFNode
from pxo_rigging_kit.maya_utils.deformers import blendshape_utils


class mirror_rbf_file(object):
    """Class to mirror 'L_' keys/strings to 'R_' in an RBF JSON file via a cmds UI.
    Only adds mirrored keys that don't exist in the original dictionary."""

    def __init__(self):
        if cmds.window("mirrorRBFWindow", exists=True):
            cmds.deleteUI("mirrorRBFWindow")
        self.window = cmds.window(
            "mirrorRBFWindow", title="Mirror RBF File", sizeable=False
        )
        self.layout = cmds.columnLayout(adjustableColumn=True)
        self.input_field = cmds.textFieldButtonGrp(
            label="Input File", buttonLabel="Browse", bc=self.select_input
        )
        self.output_field = cmds.textFieldButtonGrp(
            label="Output File", buttonLabel="Browse", bc=self.select_output
        )
        cmds.button(label="Run", command=lambda *args: self.run_mirror())
        cmds.showWindow(self.window)

    def select_input(self, *args):
        file_path = cmds.fileDialog2(
            fileMode=1, caption="Select Input RBF File"
        )
        if file_path:
            cmds.textFieldButtonGrp(self.input_field, e=True, text=file_path[0])

    def select_output(self, *args):
        file_path = cmds.fileDialog2(
            fileMode=0, caption="Select Output RBF File"
        )
        if file_path:
            cmds.textFieldButtonGrp(
                self.output_field, e=True, text=file_path[0]
            )

    def mirror_dict(self, d):
        if isinstance(d, dict):
            return {
                self.mirror_string(k): self.mirror_dict(v) for k, v in d.items()
            }
        elif isinstance(d, list):
            return [self.mirror_dict(item) for item in d]
        elif isinstance(d, str):
            return self.mirror_string(d)
        else:
            return d

    def mirror_string(self, s):
        # Non modificare stringhe con controlli centrali
        if "_C_" in s or "_C0_" in s:
            return s
        return s.replace("L_", "R_")

    def run_mirror(self, *args):
        input_path = cmds.textFieldButtonGrp(
            self.input_field, q=True, text=True
        )
        output_path = cmds.textFieldButtonGrp(
            self.output_field, q=True, text=True
        )
        if input_path and output_path:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mirrored_data = self.mirror_dict(data)
            new_keys = {k: v for k, v in mirrored_data.items() if k not in data}
            data.update(new_keys)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            cmds.confirmDialog(title="Done", message="File saved.")


class RBFWrap:
    """Create corrective blendShape RBF setups with a neutral default pose."""

    def __init__(self, name="rbfSetup"):
        self.name = name
        self.driver = ""
        self.driver_attr = ""  # For direct connections
        self.blendshape = ""
        self.control = ""
        self.parent = "setup"
        self._poses = []

    def add_pose(self, targets, rotation, control=None):
        """Add a pose to the RBF setup."""
        self._poses.append(
            (
                [targets] if isinstance(targets, str) else targets,
                rotation,
                control,
            )
        )
        return self

    def _create_missing_blendshape_targets(self, blendshape_node, target_names):
        node = (
            blendshape_node.nodeName()
            if hasattr(blendshape_node, "nodeName")
            else str(blendshape_node)
        )

        base_geo = pmc.blendShape(node, q=True, g=True)[0]
        aliases = pmc.aliasAttr(node, q=True) or []
        existing = set(aliases[0::2])

        if existing:
            print(f"Existing targets in {node}: {existing}")

        targets_to_create = target_names - existing
        if targets_to_create:
            print(f"Creating new targets: {targets_to_create}")

        for tgt in sorted(targets_to_create):
            tmp = pmc.duplicate(base_geo, n=f"{tgt}_tmp")[0]

            weight_indices = pmc.getAttr(f"{node}.weight", multiIndices=True) or []
            idx = max(weight_indices) + 1 if weight_indices else 0
            print(f"Using index {idx} for target {tgt}")

            pmc.blendShape(node, e=True,
                           t=(base_geo, idx, tmp, 1.0),
                           tangentSpace=False)
            pmc.aliasAttr(tgt, f"{node}.w[{idx}]")
            pmc.delete(tmp)

            try:
                attr_path = f"{node}.{tgt}"
                if not pmc.getAttr(attr_path, lock=True) and not pmc.listConnections(attr_path, s=True, d=False):
                    pmc.setAttr(attr_path, 0)
            except Exception as e:
                print(f"Note: Could not reset {tgt} to 0: {e}")

    def _create_rbf_node(self, driven_attrs):
        """Create and configure the RBF node."""
        # Get existing nodes before creating RBF
        existing_nodes = set(pmc.ls(type="transform"))

        rbf = RBFNode(f"{self.name}_RBF")
        rbf.setSetupName(self.name)
        rbf.setDriverNode(self.driver, ["rotateX", "rotateY", "rotateZ"])

        if hasattr(rbf, "setDriverControlAttr"):
            rbf.setDriverControlAttr(self.driver)

        rbf.setDrivenNode(self.blendshape, driven_attrs, parent=False)
        rbf.addPose([0, 0, 0], [0] * len(driven_attrs), 0)

        for i, (targets, rot, _) in enumerate(self._poses, 1):
            rbf.addPose(
                rot,
                [1.0 if attr in targets else 0.0 for attr in driven_attrs],
                i,
            )

        # Parent newly created nodes
        if self.parent and pmc.objExists(self.parent):
            # Get new nodes created after RBF setup
            new_nodes = set(pmc.ls(type="transform")) - existing_nodes

            # Look for RBF-related nodes
            rbf_nodes = []
            for node in new_nodes:
                node_name = node.name()
                # Check for various possible RBF node patterns
                if any(pattern in node_name for pattern in [
                    "weightDriver",
                    "RBF",
                    self.name,
                    "rbfSolver"
                ]):
                    # Make sure it's a top-level node (not already parented)
                    if not node.getParent():
                        rbf_nodes.append(node)

            # Parent the nodes
            if rbf_nodes:
                for node in rbf_nodes:
                    try:
                        pmc.parent(node, self.parent)
                        print(f"Parented {node} to {self.parent}")
                    except Exception as e:
                        print(f"Could not parent {node}: {e}")
            else:
                # Fallback: try to find nodes by name pattern
                patterns = [
                    f"*{self.name}*",
                    "*weightDriver*",
                    "*rbfSolver*",
                    "*RBF*"
                ]

                for pattern in patterns:
                    nodes = pmc.ls(pattern, type="transform")
                    for node in nodes:
                        if not node.getParent():  # Only parent top-level nodes
                            try:
                                pmc.parent(node, self.parent)
                                print(f"Parented {node} to {self.parent}")
                                break  # Stop after first successful parent
                            except Exception as e:
                                continue

    def _add_remap_connections(self):
        """Add remapValue node between RBF and blendshape for ALL targets."""
        targets = {t for pose in self._poses for t in pose[0]}

        ctrl_map = {}
        for targets_list, _, control in self._poses:
            ctrl = control or self.control
            if ctrl:
                for t in targets_list:
                    if t not in ctrl_map:
                        ctrl_map[t] = ctrl

        for target in sorted(targets):
            bs_attr = f"{self.blendshape}.{target}"
            src = pmc.listConnections(bs_attr, p=1, d=0, s=1)

            if not src:
                print(f"Warning: No connection found for {bs_attr}")
                continue

            pmc.disconnectAttr(src[0], bs_attr)

            remap = pmc.createNode("remapValue", n=f"{target}_remap")
            remap.inputMin.set(0)
            remap.inputMax.set(1)
            remap.outputMin.set(0)
            remap.outputMax.set(1)

            if target in ctrl_map:
                pma = pmc.createNode("plusMinusAverage", n=f"{target}_pma")
                clamp = pmc.createNode("clamp", n=f"{target}_clamp")

                pma.operation.set(1)
                clamp.min.set([0, 0, 0])
                clamp.max.set([1, 1, 1])

                src[0] >> pma.input1D[0]
                pmc.PyNode(ctrl_map[target]).translateY >> pma.input1D[1]
                pma.output1D >> clamp.inputR
                clamp.outputR >> remap.inputValue
            else:
                src[0] >> remap.inputValue

            remap.outValue >> pmc.PyNode(self.blendshape).attr(target)

    def build(self):
        """Build the RBF setup."""
        if not all([self.driver, self.blendshape, self._poses]):
            raise RuntimeError("Driver, blendshape, and poses required")

        bs_node = pmc.PyNode(self.blendshape)
        targets = {t for pose in self._poses for t in pose[0]}

        self._create_missing_blendshape_targets(bs_node, targets)
        self._create_rbf_node(sorted(targets))
        self._add_remap_connections()

    def build_direct(self):
        """Build direct connections without RBF node."""
        if not all([self.driver, self.driver_attr, self.blendshape, self._poses]):
            raise RuntimeError("Driver, driver_attr, blendshape, and poses required")

        bs_node = pmc.PyNode(self.blendshape)
        targets = {t for pose in self._poses for t in pose[0]}

        self._create_missing_blendshape_targets(bs_node, targets)

        target_configs = {}
        for targets_list, values, control in self._poses:
            for target in targets_list:
                if target not in target_configs:
                    target_configs[target] = (values, control)

        driver_node = pmc.PyNode(self.driver)
        driver_attr = driver_node.attr(self.driver_attr)

        for target in sorted(targets):
            bs_attr = f"{self.blendshape}.{target}"

            existing_connections = pmc.listConnections(bs_attr, s=True, d=False, p=True)
            if existing_connections:
                for conn in existing_connections:
                    pmc.disconnectAttr(conn, bs_attr)

            values, control = target_configs[target]
            input_min, input_max = values

            remap = pmc.createNode("remapValue", n=f"{target}_remap")
            remap.inputMin.set(input_min)
            remap.inputMax.set(input_max)
            remap.outputMin.set(0)
            remap.outputMax.set(1)

            if control:
                pma = pmc.createNode("plusMinusAverage", n=f"{target}_pma")
                clamp = pmc.createNode("clamp", n=f"{target}_clamp")

                pma.operation.set(1)
                clamp.min.set([0, 0, 0])
                clamp.max.set([1, 1, 1])

                driver_attr >> pma.input1D[0]
                pmc.PyNode(control).translateY >> pma.input1D[1]
                pma.output1D >> clamp.inputR
                clamp.outputR >> remap.inputValue
            else:
                driver_attr >> remap.inputValue

            remap.outValue >> pmc.PyNode(self.blendshape).attr(target)

    def build_mirror(self, mirror_axis=None):
        """Build a mirrored version of the RBF setup (L to R or R to L).

        Args:
            mirror_axis (str): Axis to mirror ('X', 'Y', 'Z'). If specified, inverts that axis value.
        """

        def mirror(s):
            """Mirror L/R side prefix in node names"""
            if not s:
                return s

            if s.startswith("L_"):
                return "R_" + s[2:]
            elif s.startswith("R_"):
                return "L_" + s[2:]

            return s

        def mirror_rotation(rot, axis):
            """Mirror rotation values based on specified axis"""
            if not axis:
                return rot

            new_rot = list(rot)
            if axis.upper() == 'X':
                new_rot[0] = -new_rot[0]
            elif axis.upper() == 'Y':
                new_rot[1] = -new_rot[1]
            elif axis.upper() == 'Z':
                new_rot[2] = -new_rot[2]
            return new_rot

        mirrored_name = mirror(self.name)
        mirrored_driver = mirror(self.driver)

        # Skip if nothing to mirror (central controls)
        if mirrored_name == self.name and mirrored_driver == self.driver:
            print(f"Skipping mirror for {self.name} - no L/R elements to mirror")
            return None

        m = RBFWrap(mirrored_name)
        m.driver = mirrored_driver
        m.blendshape = mirror(self.blendshape)
        m.control = mirror(self.control)
        m.parent = self.parent
        m._poses = [
            ([mirror(t) for t in tgts], mirror_rotation(rot, mirror_axis), mirror(ctrl) if ctrl else None)
            for tgts, rot, ctrl in self._poses
        ]

        print(f"Building mirrored: {m.name} (mirror_axis={mirror_axis})")
        m.build()
        return m

    def build_mirror_direct(self, mirror_axis=None):
        """Build a mirrored version of the direct setup (L to R or R to L).

        Args:
            mirror_axis (str): Axis to mirror ('X', 'Y', 'Z'). If specified, inverts that axis value.
        """

        def mirror(s):
            """Mirror L/R side prefix in node names"""
            if not s:
                return s

            if s.startswith("L_"):
                return "R_" + s[2:]
            elif s.startswith("R_"):
                return "L_" + s[2:]

            return s

        mirrored_name = mirror(self.name)
        mirrored_driver = mirror(self.driver)

        # Skip if nothing to mirror (central controls)
        if mirrored_name == self.name and mirrored_driver == self.driver:
            print(f"Skipping mirror for {self.name} - no L/R elements to mirror")
            return None

        m = RBFWrap(mirrored_name)
        m.driver = mirrored_driver
        m.driver_attr = self.driver_attr
        m.blendshape = mirror(self.blendshape)
        m.control = mirror(self.control)
        m.parent = self.parent
        m._poses = [
            ([mirror(t) for t in tgts], values, mirror(ctrl) if ctrl else None)
            for tgts, values, ctrl in self._poses
        ]

        print(f"Building mirrored direct: {m.name}")
        m.build_direct()
        return m

    def build_all(self, mirror_axis=None):
        """Build both normal and mirrored RBF setups.

        Args:
            mirror_axis (str): Axis to mirror ('X', 'Y', 'Z'). If specified, inverts that axis value.
        """
        print(f"Building primary: {self.name}")
        self.build()
        result = self.build_mirror(mirror_axis)
        if not result:
            print("Mirror setup not needed for central controls")

    def build_all_direct(self):
        """Build both normal and mirrored direct setups."""
        print(f"Building primary direct: {self.name}")
        self.build_direct()
        result = self.build_mirror_direct()
        if not result:
            print("Mirror setup not needed for central controls")


def make_rbf_corrective(name, driver, blendshape, pose_defs, parent="setup", mirror_axis=None):
    """Create RBF corrective setup with optional axis mirroring.

    Args:
        name (str): Setup name
        driver (str): Driver joint node
        blendshape (str): Target blendshape node
        pose_defs (list): List of (targets, rotation, optional_control) tuples
        parent (str): Parent group for organization
        mirror_axis (str): Axis to mirror ('X', 'Y', 'Z', or None)
    """
    r = RBFWrap(name)
    r.driver = driver
    r.blendshape = blendshape
    r.parent = parent
    for tgts, rot, ctrl in pose_defs:
        r.add_pose(tgts, rot, ctrl)
    r.build_all(mirror_axis)


def make_direct_corrective(name, driver, driver_attr, blendshape, poses, parent="setup"):
    """Create direct corrective connections without RBF."""
    r = RBFWrap(name)
    r.driver = driver
    r.driver_attr = driver_attr
    r.blendshape = blendshape
    r.parent = parent
    for tgts, values, ctrl in poses:
        r.add_pose(tgts, values, ctrl)
    r.build_all_direct()

# Example usage
# rbf = RBFWrap("shoulderRbf")
# rbf.driver = "L_bnd_clavicle_0_0_jnt"
# rbf.blendshape = "blendShape1"
# rbf.control = "pecClavMusc_L_0_default_ctrl"  # optional global control
#
# rbf.add_pose(["shoulder_down", "shoulder_down_fix"], [0, 0, 45], "pecClavMusc_L_0_default_ctrl")
# rbf.add_pose(["shoulder_up", "shoulder_up_fix"], [0, 0, -45])  # no control specified
# rbf.build()
# rbf.build_mirror()

# rbf = RBFWrap("shoulderRbf")
# rbf.driver = "L_bnd_clavicle_0_0_jnt"
# rbf.blendshape = "blendShape1"
# # rbf.control = "pecClavMusc_L_0_default_ctrl"  # control globale opzionale
#
# # control specificato per questa pose
# rbf.add_pose(["shoulder_down", "shoulder_down_fix"], [0, 0, 45], "pecClavMusc_L_0_default_ctrl")
# rbf.add_pose(["shoulder_up", "shoulder_up_fix"], [0, 0, -45])
# rbf.build()
# rbf.build_mirror()

# make_rbf_corrective(
#     "shoulderRbf",
#     "L_bnd_clavicle_0_0_jnt",
#     "blendShape1",
#     [
#         (["shoulder_down", "shoulder_down_fix"], [0, 0, 45],
#          "pecClavMusc_L_0_default_ctrl"),
#         (["shoulder_up",   "shoulder_up_fix"],   [0, 0,-45], None),
#     ],
# )

# make_direct_corrective(
#     "breathing",
#     "breathing_ctrl",
#     "translateX",
#     "blendShape1",
#     [
#         (["shoulder_down", "shoulder_down_fix"], [0, 5], "pecClavMusc_L_0_default_ctrl"),
#         (["shoulder_up", "shoulder_up_fix"], [0, -2], None),
#     ],
# )