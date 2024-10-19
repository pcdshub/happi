348 ECS-6433 heuristic loading
#################

API Breaks
----------
- N/A

Features
--------
- Updated happi's load() function to support searching and loading in one user-friendly expression. The load function gathers the results of each search term individually and loads the union of the results.

Bugfixes
--------
- N/A

Maintenance
-----------
- Cleaned up code by removing stray print() statements.
- Added unit tests for the new feature.
- In the load function of cli.py removed `term=[]` and replaced with `[item]` for readability.

Contributors
------------
- N/A
