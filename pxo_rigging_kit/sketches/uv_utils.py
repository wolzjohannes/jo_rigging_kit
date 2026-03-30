from maya.api import OpenMaya as om2
from pprint import pprint
import numpy as np
import numpy.ma as ma

sel = om2.MGlobal.getSelectionListByName("body_C_003_proxy_geo")

sel_dag = sel.getDagPath(0)

mfn_mesh = om2.MFnMesh(sel_dag)

uv_names = mfn_mesh.getUVSetNames()

us, vs = mfn_mesh.getUVs()
vtx_ids = mfn_mesh.getPoints()

assert (len(us) == len(vs))

u_arr = np.array(us, dtype=np.float32)

v_arr = np.array(vs, dtype=np.float32)

vert_index = np.arange(len(us), dtype=int)

uv_dim_array = np.column_stack((us, vs,))

uv_positions = np.floor(uv_dim_array).astype(int)

u_freq = np.unique(np.floor(u_arr, ).astype(int))
v_freq = np.unique(np.floor(v_arr, ).astype(int))

masks = dict()

for u_index in u_freq:
    for v_index in v_freq:
        mask_name = f"u__{str(u_index)}_v__{str(v_index)}"

        numpy_mask = np.where((u_arr > u_index) & (u_arr < u_index + 1) & (v_arr > v_index) & (v_arr < v_index + 1),
                              True, False)
        numpy_mask_truths = np.count_nonzero(numpy_mask)

        masks[mask_name] = (numpy_mask, numpy_mask_truths)

assert sum([x[-1] for x in masks.values()]) == len(us)

# u_arr_masked = ma.masked_array(u_arr, mask=masks["u__4_v__0"][0])

# u_arr = u_arr_masked-10.0

new_u_arr = u_arr.tolist()
print(len(new_u_arr))
print("in here")

np.multiply(u_arr, 10, where=masks["u__4_v__0"][0])
pprint(u_arr.tolist())

mfn_mesh.clearUVs(uvSet='map1')

mfn_mesh.setUVs(u_arr.tolist(), vs, uvSet='map1')
mfn_mesh.assignUVs(range(len(us)), range(len(vtx_ids)))








