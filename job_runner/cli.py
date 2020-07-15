# ModBay generic job runner.
# Copyright (C) 2020  Eugene Ershov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse

parser = argparse.ArgumentParser(
    prog="mb_backend", description="ModBay generic job runner"
)
parser.add_argument(
    "--verbosity",
    "-v",
    choices=["critical", "error", "warning", "info", "debug"],
    default="info",
    help="Verbosity level. WARNING: debug level may expose credentials",
)

args = parser.parse_args()
