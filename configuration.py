#!/usr/bin/env python
# encoding: utf-8
"""
configuration.py

Created by Patrick Shaner 2018-08-14
Modified by Patrick Shaner 2018-10-18

Copyright (c) 2018 Apple Inc., All rights reserved
THE INFORMATION CONTAINED HEREIN IS PROPRIETARY AND CONFIDENTIAL
TO APPLE, INC. USE, REPRODUCTION, OR DISCLOSURE IS SUBJECT TO PRE-APPROVAL
BY APPLE, INC.


Modified 2018-10-18
    Optimized imports
    Updated code to match style guide references Version 2.0
        - private variables have been updated with a leading '_'
        - Updated private functions with leading '_'

"""

import getpass
import json
import os
import platform

__all__ = ["test_platform", "configuration_class"]


this_file_dir = os.path.dirname(os.path.realpath(__file__))


def test_platform():
    """
    Used to determine the platform testing on.  Will created in the config to avoid circular references
    :return: Platform testing is being executed on

    """
    _platform = platform.system()
    hardware_plat = ""

    # -----------------------------------------------
    # Assigns the platform
    # -----------------------------------------------
    if str(_platform).lower() == "linux" or str(_platform).lower() == "linux2":
        hardware_plat = "Linux"

    elif str(_platform).lower() == "darwin":
        hardware_plat = "macOS"

    elif str(_platform).lower() == "win32" or str(_platform).lower() == "windows":
        hardware_plat = "Windows"

    return hardware_plat


class ConfigurationError(Exception):
    pass


class Configuration(object):
    """
    :Summary:
    Configuration class is a class that creates an objects with multiple attributes leveraged by automation.

    :How to use:
    There are two ways to utilize this module.

    First can initialize the class and it will read the generic configuration JSON based on the hardware
    code is running on. This process is the most common mode used for automation in TestOS systems.

    Second a user can set the environment variable "CONFIG" with a file path to a local JSON file. This JSON
    file can overwrite all default attributes, add new ones or only partially overwrite default config files.

    Example:
        User is running automation on local system with a system password. User can create a JSON with the key
        of "admin_pass" and assign the value as the OS admin password.  Once this is done the framework will append
        the admin password to all sudo test command when needed.

    :Resources:
    Sample Config file path:
        /sample_code/sample_config.json

    """
    env_var = "CONFIG"                          # Environment variable utilized for assigning custom config
    _sample_path = None                         # Used as for logging the file path to sample code config JSON
    _custom_config_path = None                  # The file path to the custom config file passed in from env_var
    _default_config_path = None                 # The file path to config file for platform in code base
    _default_configuration_json_data = None     # JSON data for testing platform stored in the code base
    _custom_configuration_json_data = None      # JSON data from the custom config path

    def __init__(self):
        """
        Initialize Configuration object.  Assigns the default path using current
        testing platform sets the sample config path
        """
        self._default_config_path = os.path.join(this_file_dir, "settings",
                                                 "default_{}_configuration.json".format(test_platform()))
        self._sample_path = os.path.join(os.path.abspath(os.path.join(__file__, "..", "..", "..")),
                                         "sample_code", "sample_common_config.json")

        # This should never be hit but validation that default config file exist unless code package
        # is messed up or config class was moved
        if not os.path.exists(self._default_config_path):
            raise ConfigurationError("Config file path does not exist {}".format(self._default_config_path))

        if not os.path.exists(self._sample_path):
            raise ConfigurationError("Config file path does not exist {}".format(self._sample_path))

    def config(self):
        """
        Used as the primary call point
        :return:
        """
        try:
            self._read_env_variable_and_validate_config_paths_exist()
            self._ensure_custom_config_path_ends_in_json()

            if self._custom_config_path:
                self._read_custom_json_config_file_validate_keys()

            self._combine_custom_json_and_default_json_assigning_class_attributes()
            self._set_logs_and_config_path()
            self._ensure_required_paths_exist()
            self._log_results_info()
            return self

        except Exception as e:
            print("Failed to complete setting configuration, {}".format(e))
            print("Sample file is located - {}".format(self._sample_path))
            raise e

    def _combine_custom_json_and_default_json_assigning_class_attributes(self):
        """
        Used to set attributes for class reading from custom config json file
        :return:
        """
        for default_key in self._default_configuration_json_data.keys():

            attr_name = str(default_key).lower()
            expected_type = type(self._default_configuration_json_data[default_key]["value"])
            data, settings = self._get_settings_and_value_from_config_json(default_key)

            if not isinstance(data, expected_type):
                print("expected type - {} value - {} type {}".format(expected_type, data, type(data)))
                raise ConfigurationError("{} is not supported type {}".format(default_key, expected_type))

            self._set_config_attribute(str(attr_name), data)

            if settings:
                self._set_settings_attributes(settings, default_key)

    def _ensure_custom_config_path_ends_in_json(self):
        """
        Used to read the file path, if file is ini will use config parser to read, if json then will use json load

        :exception:
        Exception is raised if file path does not end in json
        """
        if not self._custom_config_path.endswith("json"):
            raise ConfigurationError("Framework only supports json config files. "
                                     "An example configuration file can be found {}".format(self._sample_path))

    def _ensure_required_paths_exist(self):
        """
        Used to validate that all the expected directories exist before testing starts
        :return:

        :: Notes::

        This can introduce performance issues as function is called for every file that imports

        """
        for file_attr in ["logs_path", "download_path", "config_path"]:
            expected_path = getattr(self, str(file_attr), None)
            if not expected_path:
                raise ConfigurationError("Required attribute {} is not set".format(file_attr))

            if not os.path.exists(expected_path):
                os.makedirs(getattr(self, str(file_attr)))

    def _get_settings_and_value_from_config_json(self, default_key):
        """
        Used to read the config file and return the settings, value items from configuration json file.
        :param default_key: The key as string to look for
        :return: Tuple of value for key being index 0 and dictionary or none for settings
        """

        if default_key in self._custom_configuration_json_data.keys():
            data = self._custom_configuration_json_data[default_key]["value"]
            if "settings" in self._custom_configuration_json_data[default_key].keys():
                settings = self._custom_configuration_json_data[default_key]["settings"]
            else:
                settings = None
        else:
            data = self._default_configuration_json_data[default_key]["value"]
            if "settings" in self._default_configuration_json_data[default_key].keys():
                settings = self._default_configuration_json_data[default_key]["settings"]
            else:
                settings = None

        return data, settings

    def _log_results_info(self):
        """
        Used to log the download and log path for messaging
        :return: None
        """
        logs = getattr(self, "logs_path", None)
        downloads = getattr(self, "download_path", None)
        config_log = getattr(self, "config_log_path", None)

        if logs:
            print("Logs will be saved {}".format(logs))

        if downloads:
            print("Downloads will be saved {}".format(downloads))

        if config_log:
            print("Downloads will be saved {}".format(config_log))

    def _read_custom_json_config_file_validate_keys(self):
        """
        Reads custom config data from json file.
        :return:
        """
        self._default_configuration_json_data = self._read_json_file(self._default_config_path)
        self._custom_configuration_json_data = self._read_json_file(self._custom_config_path)

        diffs = list(set(self._custom_configuration_json_data) - set(self._default_configuration_json_data))

        if diffs:
            raise ConfigurationError("{} key is not supported. "
                                     "Supported keys are {}".format(diffs,
                                                                    self._default_configuration_json_data.keys()))

    def _read_env_variable_and_validate_config_paths_exist(self):
        """
        Used to check both environment variables or expected directories to get a config file.

        :exception:
        Raised if custom config or default config does not exist
        """
        self._custom_config_path = os.environ.get(self.env_var, str(self._default_config_path))

        if not os.path.exists(self._custom_config_path):
            raise ConfigurationError("Config file path does not exist {}".format(self._custom_config_path))

    def _set_settings_attributes(self, settings, default_key):
        """
        Used to iterate over the settings dictionary and append key name to settings keys then assign those attributes
        :param settings: dictionary to iterate over
        :param default_key: Attribute name to append
        :return: None
        """
        for settings_key in settings.keys():
            expected_type = type(self._default_configuration_json_data[default_key]["settings"][settings_key])
            data = settings[settings_key]

            if not isinstance(data, expected_type):
                raise ConfigurationError("{} is not supported type {}".format(default_key, expected_type))

            # look for special character like $HOME or $USER or '~'
            attr_name = "{}_{}".format(str(default_key).lower(), str(settings_key).lower())
            self._set_config_attribute(attr_name, data)

    def _set_config_attribute(self, key, value):
        """
        Used to function as a single set attribute call, also allows custom logic on the attribute
        like handling user paths
        :param key: Attribute name
        :param value: Value to set for attribute
        :return: None
        """

        special_strings = ["~", "%USERPROFILE%"]
        updated_value = value

        if isinstance(value, unicode):
            for special_values in special_strings:
                if special_values in value:
                    if special_values == "~":
                        updated_value = os.path.expanduser(str(value))
                        break
                    elif special_values == "%USERPROFILE%":
                        updated_value = str(value).replace(special_values, getpass.getuser())
                        break

        setattr(self, key, updated_value)

    def _set_logs_and_config_path(self):
        """
        Used to set the logs_path and config_path, the log_path will look first for env variables
        set by the automation harness.
        """
        log_path = None
        config_path = getattr(self, "logs_path")

        if "ATF_RESULTSDIRECTORY" in os.environ:
            log_path = os.environ["ATF_RESULTSDIRECTORY"]

        elif "TESTRESULTPATH" in os.environ:
            log_path = os.environ["TESTRESULTPATH"]

        elif "BARLI_DEST_PATH" in os.environ:
            log_path = os.environ["BARLI_DEST_PATH"]

        if log_path:
            setattr(self, "logs_path", os.path.join(log_path, "Automation_Logs"))

        setattr(self, "config_path", str(config_path))

    @staticmethod
    def _read_json_file(file_path):
        """
        Reads a json file and returns json object
        :param file_path:
        :return:
        """
        with open(file_path, "r") as f_in:
            data = json.load(f_in)

        if not data:
            raise ConfigurationError("{} is empty or did not contain a json".format(file_path))
        else:
            return data


tmp = Configuration()
configuration_class = tmp.config()
