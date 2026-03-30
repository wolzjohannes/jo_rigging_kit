import mgear.shifter.custom_step as cstp
import maya.cmds as cmds
import mgear
import os

class CustomShifterStep(cstp.customShifterMainStep):
    def setup(self):
        self.name = "pxo_rbf_volume_setup"
        project_path = cmds.workspace(query=True, rootDirectory=True)
        self.path = os.path.normpath(os.path.join(project_path, "data", "rbf_volume_joint.rbf"))
    
    def _create_constraint(self, jnt_01, jnt_02, vol_ctrl, maintain_offset=True, interp_type=2, weight_value=1, vol_ctrl_shape_value=0):
        if not (cmds.objExists(jnt_01) and cmds.objExists(jnt_02) and cmds.objExists(vol_ctrl)
        and cmds.objExists(vol_ctrl_shape_value)):
            cmds.warning(f"Cannot create constraint: one or more required objects do not exist.{jnt_01},{jnt_02},{vol_ctrl} ")
            return None
        constraint = cmds.parentConstraint(jnt_01, jnt_02, vol_ctrl, mo=maintain_offset)[0]
        cmds.setAttr(f"{constraint}.interpType", interp_type)
        cmds.setAttr(f"{constraint}.{jnt_01}W0", weight_value)
        cmds.setAttr(f"{vol_ctrl}Shape.v", vol_ctrl_shape_value)
        return constraint

    def run(self):
        
        for side in ("L", "R"):
            self._create_constraint(
                jnt_01=f"{side}_bnd_shoulder_0_shoulder_jnt",
                jnt_02=f"{side}_bnd_arm_0_0_jnt",
                vol_ctrl=f"VolShoulderMaster_{side}_0_vol_ctrl",
                weight_value=2
            )
            self._create_constraint(
                jnt_01=f"{side}_bnd_arm_0_end_jnt",
                jnt_02=f"{side}_bnd_arm_0_8_jnt",
                vol_ctrl=f"VolWristMaster_{side}_0_vol_ctrl"
            )
            self._create_constraint(
                jnt_01="C_bnd_hip_0_1_jnt",
                jnt_02=f"{side}_bnd_leg_0_0_jnt",
                vol_ctrl=f"VolHipMaster_{side}_0_vol_ctrl"
            )
            self._create_constraint(
                jnt_01=f"{side}_bnd_leg_0_8_jnt",
                jnt_02=f"{side}_bnd_foot_0_0_jnt",
                vol_ctrl=f"VolAnkleMaster_{side}_0_vol_ctrl",
                weight_value=0.2
            )
            
        mgear.rigbits.rbf_io.importRBFs(self.path)
        
        attributes = [
        "L_VolAnkle_df_cons_vis", "R_VolAnkle_df_cons_vis",
        "L_VolAnkleMaster_df_cons_vis", "R_VolAnkleMaster_df_cons_vis",
        "L_VolElbow_df_cons_vis", "R_VolElbow_df_cons_vis",
        "L_VolHip_df_cons_vis", "R_VolHip_df_cons_vis",
        "L_VolHipMaster_df_cons_vis", "R_VolHipMaster_df_cons_vis",
        "L_VolKnee_df_cons_vis", "R_VolKnee_df_cons_vis",
        "L_VolShoulder_df_cons_vis", "R_VolShoulder_df_cons_vis",
        "L_VolShoulderMaster_df_cons_vis", "R_VolShoulderMaster_df_cons_vis",
        "L_VolWrist_df_cons_vis", "R_VolWrist_df_cons_vis",
        "L_VolWristMaster_df_cons_vis", "R_VolWristMaster_df_cons_vis"
        ]

        for attr in attributes:
            cmds.setAttr(f"visibility_C_0_ctrl.{attr}", 0)
        return
