
WORK_DIR=$1
SPARSE_INDEX=$2

IMG_PATH=$WORK_DIR/frames
INPUT_PATH=$WORK_DIR/colmap/sparse/$SPARSE_INDEX
OUTPUT_PATH=$WORK_DIR/colmap/dense

OLD_DIR=$(pwd)

mkdir -p $OUTPUT_PATH

colmap image_undistorter   \
   --image_path $IMG_PATH \
   --input_path $INPUT_PATH  \
   --output_path $OUTPUT_PATH   \
   --output_type COLMAP   \
   --max_image_size 1000 \

cd $OUTPUT_PATH

colmap patch_match_stereo    \
--workspace_path .    \
--workspace_format COLMAP    \
--PatchMatchStereo.max_image_size=1000     \
--PatchMatchStereo.gpu_index=0,1     \
--PatchMatchStereo.cache_size=32 \
--PatchMatchStereo.geom_consistency false \

colmap stereo_fusion   \
  --workspace_path .   \
  --workspace_format COLMAP   \
  --input_type photometric   \
  --output_type PLY \
  --output_path ./fused.ply \

# For geometric consistency, do the following lines instead
# colmap patch_match_stereo    \
# --workspace_path .    \
# --workspace_format COLMAP    \
# --PatchMatchStereo.max_image_size=1000     \
# --PatchMatchStereo.gpu_index=0,1     \
# --PatchMatchStereo.cache_size=32 \
# --PatchMatchStereo.geom_consistency false \

# colmap stereo_fusion   \
#   --workspace_path .   \
#   --workspace_format COLMAP   \
#   --input_type photometric   \
#   --output_type PLY \
#   --output_path ./fused.ply \

cd $OLD_DIR