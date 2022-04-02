import os
from functools import partial
from datadog import initialize, statsd

STATSD_HOST = "statsd-exporter"
STATSD_PORT = "9125"

def setting_statsd():
    statsd_options = {
        "statsd_host": os.getenv("STATSD_HOST", STATSD_HOST),
        "statsd_port": os.getenv("STATSD_PORT", STATSD_PORT)
    }

    initialize(**statsd_options)


class StatsdMiddleware:
    def __init__(self, application, app_name):
        self.__application = application
        self.__app_name = app_name

        # send service info with tags
        statsd.gauge("flask.info", 1, tags=[
            f"app_name:{self.__app_name}",
        ])

    def __call__(self, environ, start_response):
        patch_info = {
            "app_name": self.__app_name, 
            "method": environ['REQUEST_METHOD'],
            "endpoint": environ['PATH_INFO']
        }

        def _start_response(status, headers, *args, **kwargs):
            # log http status code when each response start
            statsd.increment(
                f"flask.request_status_total",
                tags=[
                    f"app_name:{kwargs.get('app_name', '')}",
                    f"method:{kwargs.get('method', '')}",
                    f"endpoint:{kwargs.get('endpoint', '')}",
                    f"status:{status.split()[0]}",
                ]
            )
            return start_response(status, headers, *args)

        # timing each request
        with statsd.timed(
            f"flask.request_duration_seconds",
            tags=[
                f"app_name:{patch_info.get('app_name', '')}",
                f"method:{patch_info.get('method', '')}",
                f"endpoint:{patch_info.get('endpoint', '')}",
            ],
            use_ms=True
        ):
            return self.__application(environ, partial(_start_response, **patch_info))
