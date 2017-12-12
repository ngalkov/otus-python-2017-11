#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os.path
import argparse
import configparser
import re
import logging
import datetime
import gzip
import statistics

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

DEFAULT_CONFIG_PATH = "./log_analyzer.conf"
CONFIG_SECTION_NAME = "MAIN"
REPORT_TEMPLATE = "./report.html"
TS_FILE = "./log_analyzer.ts"
LOG_NAME_PREFIX = "nginx-access-ui.log-"


def parse_args(args):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",
                        help="path to config file",
                        default=DEFAULT_CONFIG_PATH,
                        dest="config_path")
    return parser.parse_args(args)


def load_config(config_path, default_config):
    """Return default_config updated from config_path"""
    parser = configparser.ConfigParser(defaults=default_config)
    with open(config_path) as f:
        parser.read_file(f)
    new_config = {key.upper(): value for (key, value) in parser[CONFIG_SECTION_NAME].items()}
    return new_config


def check_config(config):
    """Return description of error in config or None if no errors"""
    for key, value in config.items():
        if key == "REPORT_SIZE":
            try:
                if int(config[key]) <= 0:
                    return "REPORT_SIZE should be > 0"
            except ValueError:
                return "REPORT_SIZE should be integer"
        else:
            if not os.path.exists(config[key]):
                return "%s: %s - path doesn't exist-" % (key, config[key])
        return None
    pass


def set_logger(filename=None):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    if filename is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(filename)
    formatter = logging.Formatter("[%(asctime)s] %(levelname).1s %(message)s",
                                  datefmt="%Y.%m.%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_last_log_name(log_dir, prefix):
    """Return the latest filename

    Scan log_dir for filenames starting with prefix and return
    filename with latest date in filename or None if no such files"""
    log_names = []
    for entry in os.listdir(log_dir):
        if not os.path.isfile(os.path.join(log_dir, entry)):
            continue
        if entry.startswith(prefix):
            log_names.append(entry)
    if log_names:
        log_name = max(log_names, key=lambda filename: filename.replace(prefix, ""))
        return log_name
    else:
        return None


def extract_date(text, date_pat=r"(?P<date>\d{8})", date_fmt="%Y%m%d"):
    date_match = re.search(date_pat, text)
    if date_match:
        try:
            return datetime.datetime.strptime(date_match.group("date"), date_fmt).date()
        except ValueError:
            return None
    else:
        return None


def parse_log(log_path, logger=None):
    """Return dict in the form: {"url": [time1, time2, ...]} for unique urls in log_path"""
    line_pat = re.compile(
        r"(?P<remote_addr>[\d\.]{4})\s+"
        r"(?P<remote_user>\S+)\s+"
        r"(?P<http_x_real_ip>\S+)\s+"
        r"\[(?P<time_local>.*?)\]\s+"
        r"\"(?P<request>.*?)\"\s+"
        r"(?P<status>\d+)\s+"
        r"(?P<body_bytes_sent>\d+)\s+"
        r"\"(?P<http_referer>.*?)\"\s+"
        r"\"(?P<http_user_agent>.*?)\"\s+"
        r"\"(?P<http_x_forwarded_for>.*?\"\s+)"
        r"\"(?P<http_X_REQUEST_ID>.*?)\"\s+"
        r"\"(?P<http_X_RB_USER>.*?)\"\s+"
        r"(?P<request_time>\d*\.?\d+)\s*",
        re.VERBOSE)
    url_pat = re.compile(r"^[A-Z]+\s+(?P<url>\S+)\s+HTTP.*$")

    url_times = {}
    line_idx = 0
    for line in xreadlines(log_path):
        # for debag:
        # if line_idx % 1000 == 0: print("line %s parsed" % line_idx)
        line_idx += 1
        line_match = line_pat.search(line)
        if line_match:
            request = line_match.group("request")
            request_time = line_match.group("request_time")
            url_match = url_pat.search(request)
            if url_match:
                url = url_match.group("url")
                times = url_times.get(url, [])
                try:
                    times.append(float(request_time))
                    url_times[url] = times
                    continue
                except ValueError:
                    pass
        if logger:
            logger.error("Error in line %s: %s" % (line_idx, line.strip()))
    return url_times


def xreadlines(log_path):
    """Generator to read file one line at a time"""
    try:
        if log_path.endswith(".gz"):
            log = gzip.open(log_path, 'rt')
        else:
            log = open(log_path)
        for line in log:
            yield line
    except:
        raise
    finally:
        log.close()


def count_statistics(urls):
    request_count = 0
    total_time = 0.0
    for times in urls.values():
        request_count += len(times)
        total_time += sum(times)
    url_statistics = []
    for url, times in urls.items():
        url_statistics.append({
            "url": url,
            "count": len(times),
            "time_avg": round(statistics.mean(times), 3),
            "time_max": round(max(times), 3),
            "time_sum": round(sum(times), 3),
            "time_med": round(statistics.median(sorted(times)), 3),
            "time_perc": round(100 * sum(times) / total_time, 3),
            "count_perc": round(100 * len(times) / float(request_count), 3)
        })
    return url_statistics


def make_report(report_path, template, url_statistics):
    with open(template) as f:
        content = f.read()
    content = content.replace('$table_json', str(url_statistics))
    with open(report_path, "w") as f:
        f.write(content)
    pass


def write_timestamp(ts_file):
    """Rewrite ts_file with line containing current timestamp"""
    with open(ts_file, 'w') as f:
        f.write("%s" % datetime.datetime.now().timestamp())


def main(config):
    log_dir = config["LOG_DIR"]
    report_dir = config["REPORT_DIR"]
    report_size = int(config["REPORT_SIZE"])
    logger = set_logger(config.get("LOGGING", None))
    logger.info("Starting log analyzer")

    # Log file searching
    log_name = get_last_log_name(log_dir, LOG_NAME_PREFIX)
    if not log_name:
        logger.error("No log files found in directory %s" % log_dir)
        sys.exit()
    log_date = extract_date(log_name)
    logger.info("Last log file %s found" % os.path.join(log_dir, log_name))

    # Report file searching
    report_name, report_ext = os.path.splitext(os.path.basename(REPORT_TEMPLATE))
    report_path = os.path.join(report_dir,
                               report_name + "-" + log_date.strftime("%Y.%m.%d") + report_ext)
    if os.path.exists(report_path):
        logger.info("Report file %s already exists" % report_path)
        sys.exit()

    # Process log
    log_path = os.path.join(log_dir, log_name)
    try:
        request_times = parse_log(log_path)
    except OSError:
        logger.exception("Unable to open log file %s" % log_path)
        sys.exit()
    logger.info("%s unique urls found" % len(request_times))
    url_statistics = count_statistics(request_times)
    url_statistics.sort(reverse=True, key=lambda k: k["time_sum"])
    try:
        make_report(report_path, REPORT_TEMPLATE, url_statistics[:report_size])
        logger.info("Report file %s created successfully" % report_path)
    except OSError:
        logger.exception("Unable to create report file %s" % report_path)
        sys.exit()

    # Finish work
    write_timestamp(TS_FILE)
    logger.info("Stopping log analyzer")


if __name__ == "__main__":
    # Script initialization
    # As logger is not defined yet, send error messages to stderr
    args = parse_args(sys.argv[1:])
    try:
        config = load_config(args.config_path, DEFAULT_CONFIG)
    except OSError:
        print("Unable to open config file %s" % args.config_path, sys.stderr)
        sys.exit()
    except configparser.Error:
        print("Unable to parse config file %s" % args.config_path, sys.stderr)
        sys.exit()
    config_error = check_config(config)
    if config_error:
        print(config_error, sys.stderr)
        sys.exit()
    main(config)
