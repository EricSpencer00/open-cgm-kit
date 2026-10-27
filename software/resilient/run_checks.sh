#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rz_binary=${RZ_BIN:-rz}

"$rz_binary" --version
for program in core_tests guard_tests stress_tests demo; do
    "$rz_binary" check "$script_dir/$program.rz"
    "$rz_binary" --seed 1 --panic-on-fault "$script_dir/$program.rz"
done
