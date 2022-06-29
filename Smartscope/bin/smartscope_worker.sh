#! /bin/bash

echo 'Executing on worker.' $@

singularity exec --nv --writable-tmpfs -B $SINGULARITY_BINDS --env-file config/singularity/env.sh smartscope.sif $@
