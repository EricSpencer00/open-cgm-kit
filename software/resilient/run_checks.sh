#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
rz_binary=${RZ_BIN:-rz}

"$rz_binary" --version
"$rz_binary" check "$script_dir/core_tests.rz"
"$rz_binary" --seed 1 --panic-on-fault "$script_dir/core_tests.rz"
"$rz_binary" check "$script_dir/demo.rz"
"$rz_binary" --seed 1 --panic-on-fault "$script_dir/demo.rz"
