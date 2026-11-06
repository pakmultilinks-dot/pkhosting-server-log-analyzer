# Evaluation results

Generated fixtures only, no real customer logs. Parser run on 18 fixtures, 401 lines in total.

- Overall per-line accuracy: 100.0% (401 of 401 lines)
- Dominant problem type correct on 18 of 18 fixtures (100.0%)

| File | Format | Lines | Expected dominant | Predicted dominant | Correct | Per-line accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| apache_access_404.log | apache_access | 23 | 404_not_found | 404_not_found | yes | 100.0% |
| apache_access_500.log | apache_access | 22 | 500_server_error | 500_server_error | yes | 100.0% |
| app_auth.log | application | 24 | auth_failure | auth_failure | yes | 100.0% |
| app_db_error.log | application | 23 | database_error | database_error | yes | 100.0% |
| app_exception.log | application | 20 | app_exception | app_exception | yes | 100.0% |
| app_mixed.log | application | 22 | 500_server_error | 500_server_error | yes | 100.0% |
| app_slow.log | application | 23 | slow_request | slow_request | yes | 100.0% |
| nginx_access_404.log | nginx_access | 23 | 404_not_found | 404_not_found | yes | 100.0% |
| nginx_access_429.log | nginx_access | 20 | rate_limit | rate_limit | yes | 100.0% |
| nginx_access_500.log | nginx_access | 23 | 500_server_error | 500_server_error | yes | 100.0% |
| nginx_access_auth.log | nginx_access | 25 | auth_failure | auth_failure | yes | 100.0% |
| nginx_access_bot.log | nginx_access | 25 | bot_flood | bot_flood | yes | 100.0% |
| nginx_access_mixed.log | nginx_access | 22 | 404_not_found | 404_not_found | yes | 100.0% |
| nginx_access_slow.log | nginx_access | 23 | slow_request | slow_request | yes | 100.0% |
| nginx_access_upstream.log | nginx_access | 21 | upstream_timeout | upstream_timeout | yes | 100.0% |
| nginx_error_file.log | nginx_error | 22 | file_permission_error | file_permission_error | yes | 100.0% |
| nginx_error_ssl.log | nginx_error | 20 | ssl_error | ssl_error | yes | 100.0% |
| nginx_error_upstream.log | nginx_error | 20 | upstream_timeout | upstream_timeout | yes | 100.0% |

## Notes
All 18 fixtures classified correctly on dominant type and on per-line counts. This is expected because the fixtures were generated to match the documented parser rules, so the result shows the parser works as specified on generated data, not that it will be perfect on real-world logs.
