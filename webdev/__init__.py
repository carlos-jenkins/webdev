# Copyright (C) 2026 KuraLabs S.R.L <info@kuralabs.io>
# Copyright (C) 2015-2016 Carlos Jenkins <carlos@jenkins.co.cr>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
WebDev - a small, fast development web server.

Serves any local directory over HTTP with developer-friendly features:
graceful handling (and auto-recovery) when the served directory disappears,
incremental automatic port selection, live reload, a modern dark directory
index, optional HTTPS, and more.
"""

from __future__ import annotations

__version__ = "2.0.0"

__all__ = ["__version__"]
