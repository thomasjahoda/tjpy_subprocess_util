"""
Script to execute after creating the project.
- Encrypts the PyPi password to the .travis.yml
- Updates PyCharm configuration if detected
-- Sets the test runner to pytest
-- Excludes cache directories
"""

import configparser
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, cast, Dict, Optional
import xml.etree.ElementTree as ElementTree

try:
    import yaml
except ImportError as error:
    print("Attempting to install pyyaml")
    subprocess.run(["pip", "install", "pyyaml"])
    try:
        import yaml
    except ImportError as error:
        raise Exception(
            "Could not install pyyaml automatically successfully, please install it manually first") from error

TRAVIS_YML_FILE = Path("../.travis.yml").expanduser()
TRAVIS_YML_ENCRYPTED_PASSWORD_PLACEHOLDER_VALUE = "PLEASE_REPLACE_ME"


def encrypt_pypi_password_for_travis_if_necessary():
    travis_yml_content = yaml.safe_load(TRAVIS_YML_FILE.read_text(encoding="utf-8"))
    project_owner_pypi_username = travis_yml_content["deploy"]["user"]
    project_owner_pypi_encrypted_password = travis_yml_content["deploy"]["password"]["secure"]
    if project_owner_pypi_encrypted_password == TRAVIS_YML_ENCRYPTED_PASSWORD_PLACEHOLDER_VALUE:
        _encrypt_pypi_password_for_travis(project_owner_pypi_username)
    else:
        print(f"Travis password has already been encrypted in {TRAVIS_YML_FILE.name}.")


def _encrypt_pypi_password_for_travis(project_owner_pypi_username: str):
    pypi_username, pypi_password = _get_pypi_credentials()
    if pypi_username != project_owner_pypi_username:
        raise Exception(f"The pypi username stated in {TRAVIS_YML_FILE.name} ({project_owner_pypi_username}) "
                        f"does not match the one configured in the current environments "
                        f"pypi settings ({pypi_username}). "
                        f"Please check your ~/.pypirc file or your keyring properties for pypi.")
    try:
        result = subprocess.run(
            ["travis", "encrypt", "--skip-version-check", "--skip-completion-check", "--no-interactive"],
            input=bytes(pypi_password, encoding="utf-8"),
            capture_output=True,
        )
    except FileNotFoundError as exception:
        raise Exception("Command 'travis' needs to be available on path.\n"
                        "Please install https://github.com/travis-ci/travis.rb#installation\n"
                        "Also make sure to login via 'travis login'.\n"
                        "Generating an access token yourself is recommended though and "
                        "logging in via: travis login --github-token [token]") from exception
    result.check_returncode()
    output = str(result.stdout, encoding="utf-8")
    encrypted_password = output[1:-2]

    travis_yml_text = TRAVIS_YML_FILE.read_text(encoding="utf-8")
    travis_yml_text = travis_yml_text.replace(TRAVIS_YML_ENCRYPTED_PASSWORD_PLACEHOLDER_VALUE, encrypted_password)
    TRAVIS_YML_FILE.write_text(travis_yml_text, encoding="utf-8")
    print(f"Updated {TRAVIS_YML_FILE.name} with encrypted pypi password. Please commit it in Git.")


def _get_pypi_credentials() -> Tuple[str, str]:
    pypirc_file = Path("~/.pypirc").expanduser()
    if pypirc_file.is_file():
        config = configparser.ConfigParser()
        config.read(pypirc_file)
        pypi_username = config['pypi']['username']
        pypi_password = config['pypi']['password']
        print(f"Using pypi credentials found in {pypirc_file}")
        return pypi_username, pypi_password
    else:
        # TODO check keyring if pypi credentials are there in case ~/.pypirc does not exist.
        #  https://twine.readthedocs.io/en/latest/#id6
        raise Exception("Please create the file ~/.pypirc with your pypi user credentials as documented at "
                        "https://packaging.python.org/guides/distributing-packages-using-setuptools/#id78\n"
                        "Support for the Keyring credentials as documented at "
                        "https://twine.readthedocs.io/en/latest/#id6 is currently unsupported but contributing "
                        "is wished.")


encrypt_pypi_password_for_travis_if_necessary()


def _get_project_name():
    return cast(Path, Path.cwd()).parent.name


@dataclass
class _XmlElementData:
    tag: str
    attributes: Dict[str, str]
    identifying_attribute: str


class PyCharmConfigUpdater:

    def __init__(self):
        self.updated = False

    def update_pycharm_config(self,
                              update_testrunner_to_pytest: bool,
                              exclude_cache_and_build_directories: bool):
        project_name = _get_project_name()
        idea_project_config_file = Path("../.idea", f"{project_name}.iml")
        if idea_project_config_file.exists():
            tree = ElementTree.parse(idea_project_config_file)
            if update_testrunner_to_pytest:
                self._update_testrunner_to_pytest(tree)
            if exclude_cache_and_build_directories:
                self._exclude_cache_and_build_directories(tree)
            if self.updated:
                tree.write(idea_project_config_file, encoding="UTF-8", xml_declaration=True)
                print(f"Updated PyCharm config file {idea_project_config_file}")
            else:
                print(f"PyCharm config file {idea_project_config_file} was already correct.")
        else:
            print("No PyCharm project configuration file found.")

    def _update_testrunner_to_pytest(self, tree: ElementTree.ElementTree):
        root = tree.getroot()

        test_runner_element = self._create_or_update_element_if_necessary(root, _XmlElementData(
            tag="component",
            attributes={"name": "TestRunnerService"},
            identifying_attribute="name"
        ))
        self._create_or_update_element_if_necessary(test_runner_element, _XmlElementData(
            tag="option",
            attributes={"name": "projectConfiguration", "value": "pytest"},
            identifying_attribute="name"
        ))
        self._create_or_update_element_if_necessary(test_runner_element, _XmlElementData(
            tag="option",
            attributes={"name": "PROJECT_TEST_RUNNER", "value": "pytest"},
            identifying_attribute="name"
        ))

    def _exclude_cache_and_build_directories(self, tree: ElementTree.ElementTree):
        root = tree.getroot()

        module_root_manager_element = self._create_or_update_element_if_necessary(root, _XmlElementData(
            tag="component",
            attributes={"name": "NewModuleRootManager"},
            identifying_attribute="name"
        ))
        content_element = self._create_or_update_element_if_necessary(module_root_manager_element, _XmlElementData(
            tag="content",
            attributes={"url": "file://$MODULE_DIR$"},
            identifying_attribute="url"
        ))

        excluded_folders = [
            "file://$MODULE_DIR$/.mypy_cache",
            "file://$MODULE_DIR$/.pytest_cache",
            "file://$MODULE_DIR$/.tox",
            f"file://$MODULE_DIR$/{_get_project_name()}.egg-info",
        ]
        for excluded_folder in excluded_folders:
            self._create_or_update_element_if_necessary(content_element, _XmlElementData(
                tag="excludeFolder",
                attributes={"url": excluded_folder},
                identifying_attribute="url"
            ))

    def _create_or_update_element_if_necessary(self, parent: ElementTree.ElementTree,
                                               desired_xml_element: _XmlElementData) -> ElementTree.ElementTree:
        """
        Makes sure the parent has an sub element as described.
        :param parent:
        :param desired_xml_element:
        :return: relevant real XML element which may have been created or updated
        """
        identifying_attribute_value = desired_xml_element.attributes.get(desired_xml_element.identifying_attribute)
        searched_element = next(
            (element for element in parent.findall(desired_xml_element.tag)
             if element.get(desired_xml_element.identifying_attribute) == identifying_attribute_value), None)
        if searched_element is not None:
            for key, value in desired_xml_element.attributes.items():
                if searched_element.get(key) != value:
                    searched_element.set(key, value)
                    self.updated = True
            return searched_element
        else:
            new_element = ElementTree.SubElement(parent, desired_xml_element.tag, desired_xml_element.attributes)
            self.updated = True
            return new_element


PyCharmConfigUpdater().update_pycharm_config(
    update_testrunner_to_pytest=True,
    exclude_cache_and_build_directories=True
)
