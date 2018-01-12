#!/usr/bin/env python
# -*- coding: utf-8 -*-

from log_analyzer import *
import unittest
import datetime


# class TestCmdLoneArgs(unittest.TestCase):
#     def test_config_path_present(self):
#         args = ["--config", "./log_analyzer.conf"]
#         self.assertEqual(parse_args(args).config_path, args[1])
#
#     def test_config_path_omitted(self):
#         args = []
#         self.assertEqual(parse_args(args).config_path, DEFAULT_CONFIG_PATH)


class TestInitialization(unittest.TestCase):
    def test_load_config(self):
        default_config = {"A": "a", "B": "b", "C": "c"}
        # valid config
        self.assertDictEqual(load_config("./tests/valid_config.ini", default_config),
                          {"A": "1", "B": "", "C": "c", "D": "4"})
        # file doesn't exist
        self.assertRaises(OSError, load_config, "bad_file_name", default_config)
        # badly formatted config
        self.assertRaises(configparser.Error, load_config, "./tests/invalid_config.ini", default_config)

    def test_check_config(self):
        # noninteger REPORT_SIZE
        self.assertEqual(check_config({"REPORT_SIZE": "str"}), "REPORT_SIZE should be integer")
        # negative REPORT_SIZE
        self.assertEqual(check_config({"REPORT_SIZE": "-1"}), "REPORT_SIZE should be > 0")
        # bad path
        self.assertEqual(check_config({"PATH": "./bad_path"}), "PATH: ./bad_path - path doesn't exist-")
        # no errors
        self.assertIsNone(check_config({"REPORT_SIZE": "10", "TEST": "./tests"}))


class TestLogsProcessing(unittest.TestCase):
    def test_extract_date(self):
        # valid log name
        self.assertEqual(extract_date("log.name-20010203", r"^log.name-(?P<date>\d{8})", "%Y%m%d"),
                         datetime.date(2001, 2, 3))
        # no date
        self.assertIsNone(extract_date("no_date", r"(?P<date>\d{8})", "%Y%m%d"))
        # bad date
        self.assertIsNone(extract_date("bad.date-20019999", r"^bad.date-(?P<date>\d{8})", "%Y%m%d"))

    def test_get_last_log(self):
        # valid log name
        self.assertEqual(get_last_log_name("./tests/log", "log-test-date"), "log-test-date-20010201")
        # no log files in log dir
        self.assertIsNone(get_last_log_name("./tests/log", "no-such-log-file-"))

    def test_parse_log(self):
        # test both example logs - plain text and gzip
        # examples ./tests/log/log_example and ./tests/log/log_example.gz are equal and contain lines:
        # 1 - valid line, url - "/test/url/A", time as 0.0
        # 2 - valid line, url - "/test/url/A", time as .0
        # 3 - valid line, url - "/test/url/A", time as 0
        # 4 - valid line, url - "/test/url/B"
        # 5 - invalid line - bad time
        # 6 - invalid line - bad url
        for log_example in ["./tests/log/log_example", "./tests/log/log_example.gz"]:
            # test valid lines
            self.assertEqual(parse_log(log_example),
                             {"/test/url/A": [0.12, 0.34, 1.0], "/test/url/B": [0.123]})
            # test whether invalid lines were logged
            with self.assertLogs() as cm:
                parse_log(log_example)
            self.assertEqual(list(map(lambda t: t[:27], cm.output)),    # strip long lines for brevity
                             ['ERROR:root:Error in line 5:',
                              'ERROR:root:Error in line 6:'])

    def test_count_statistics(self):
        # test whether counted values and correct values are almost equal
        counted_urls = count_statistics(parse_log("./tests/log/log_example"))
        correct_urls = [
            {"url": "/test/url/A",
             "count": 3,
             "time_avg": 0.487,
             "time_max": 1.0,
             "time_sum": 1.46,
             "time_med": 0.34,
             "time_perc": 92.230,
             "count_perc": 75.0},
            {"url": "/test/url/B",
             "count": 1,
             "time_avg": 0.123,
             "time_max": 0.123,
             "time_sum": 0.123,
             "time_med": 0.123,
             "time_perc": 7.770,
             "count_perc": 25.0}
                ]
        for url in range(2):
            for key in correct_urls[url]:
                self.assertAlmostEqual(correct_urls[url][key], counted_urls[url][key], places=3)

    # def test_make_report(self):
    #     # test whether report file created
    #     test_value = datetime.datetime.now().timestamp()
    #     make_report("./tests/reports/report.txt", "./tests/reports/template.txt", [test_value])
    #     with open("./tests/reports/report.txt") as f:
    #         for line in f:
    #             if line.strip().startswith("var table"):
    #                 self.assertEqual(line.strip(), "var table = [%s];" % test_value)


if __name__ == '__main__':
    unittest.main()
