from dotenv import load_dotenv
import os
import mimetypes
import requests
import json
from dataclasses import dataclass
import datetime
import re
import base64
from typing import Any

# Global Variables
_current_login = None
_configured_credentials = None

# Classes
@dataclass
class Login:
    '''Class to hold API login information to facilitate easier token refreshing on time'''
    success: bool
    error: str | None
    bearer: str | None
    time_of_issue: datetime.datetime
    expiration_time: int

    def is_valid(self) -> bool:
        current_time = datetime.datetime.now()
        time_of_expiration = self.time_of_issue + datetime.timedelta(seconds=self.expiration_time)
        return current_time < time_of_expiration

# Helper Functions
def validate_time_date(time: str, date: str) -> tuple[bool, str]:
    """
    Validate time and date format.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Validate date format: yyyy-mm-dd
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, date):
        return False, "Date must be formatted as yyyy-mm-dd"
    
    # Validate time format: hh:mm:ss with optional timezone
    time_pattern = r'^\d{2}:\d{2}:\d{2}(\s+\S+)?$'
    if not re.match(time_pattern, time):
        return False, "Time must be formatted as hh:mm:ss with optional timezone"
    
    # Optional: Validate that date values are actually valid
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return False, "Date contains invalid values"
    
    # Optional: Validate time values (hours, minutes, seconds)
    time_parts = time.split()[0]  # Get just hh:mm:ss part
    try:
        datetime.datetime.strptime(time_parts, '%H:%M:%S')
    except ValueError:
        return False, "Time contains invalid values"
    
    return True, ""


def _get_request(url, params=None) -> dict:
    """Internal helper to make authenticated GET requests"""
    session = _get_valid_login()
    headers = {
        "authorization": session.bearer,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raises HTTPError for bad status codes
        return response.json()
    except requests.exceptions.HTTPError:
        return {"error": response.status_code, "details": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": "request_failed", "details": str(e)}


def _put_request(url, params=None, payload=None, raw_data=None) -> dict:
    """
    Internal helper to make authenticated PUT requests
    
    Args:
        url: API endpoint
        params: URL query parameters
        payload: JSON payload (dict) - will be serialized and sent with Content-Type: application/json
        raw_data: Raw data (for non-JSON requests) - use this OR payload, not both
    """
    session = _get_valid_login()
    headers = {"authorization": session.bearer}
    
    try:
        if raw_data is not None:
            # Send raw data without JSON encoding
            headers["Content-Type"] = "application/octet-stream"
            response = requests.put(url, headers=headers, params=params, data=raw_data)
        else:
            # Send JSON payload
            headers["Content-Type"] = "application/json"
            response = requests.put(url, headers=headers, params=params, json=payload)
        
        response.raise_for_status()
        
        # Handle 204 No Content
        if response.status_code == 204:
            return {"success": True}
        
        return response.json()
        
    except requests.exceptions.HTTPError:
        return {"error": response.status_code, "details": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": "request_failed", "details": str(e)}


def _post_request(url, params=None, payload=None, raw_data=None) -> dict:
    """Internal helper to make authenticated POST requests"""
    session = _get_valid_login()
    headers = {"authorization": session.bearer}
    
    try:
        if raw_data is not None:
            headers["Content-Type"] = "application/octet-stream"
            response = requests.post(url, headers=headers, params=params, data=raw_data)
        else:
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, params=params, json=payload)
        
        response.raise_for_status()
        
        if response.status_code == 204:
            return {"success": True}
        
        return response.json()
        
    except requests.exceptions.HTTPError:
        return {"error": response.status_code, "details": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": "request_failed", "details": str(e)}


def _delete_request(url, params=None, payload=None) -> dict:
    """Internal helper to make authenticated DELETE requests"""
    session = _get_valid_login()
    headers = {"authorization": session.bearer}
    
    try:
        if payload is not None:
            headers["Content-Type"] = "application/json"
            response = requests.delete(url, headers=headers, params=params, json=payload)
        else:
            response = requests.delete(url, headers=headers, params=params)
        
        response.raise_for_status()
        
        if response.status_code == 204:
            return {"success": True}
        
        return response.json()
        
    except requests.exceptions.HTTPError:
        return {"error": response.status_code, "details": response.text}
    except requests.exceptions.RequestException as e:
        return {"error": "request_failed", "details": str(e)}
        
# -------------------------------------------------------
#                       API CALLS
# -------------------------------------------------------

# ---------------------------------- BSN Cloud Authentication ----------------------------------
def _load_credentials() -> tuple:
    '''
    Loads BSN Cloud API credentials from multiple sources in order of priority.
    Priority 1: Explicitly set credentials via configure()
    Priority 2: Environment variables (without .env file)
    Priority 3: .env file
    '''
    # Priority 1: Explicitly set credentials via configure()
    global _configured_credentials
    if _configured_credentials:
        return _configured_credentials
    
    # Priority 2: Environment variables (without .env file)
    client_id = os.getenv('BSN_CLIENT_ID')
    secret = os.getenv('BSN_SECRET')
    network = os.getenv('BSN_NETWORK')
    
    if client_id and secret and network:
        return (client_id, secret, network)
    
    # Priority 3: .env file (current method)
    load_dotenv(override=True)
    client_id = os.getenv('BSN_CLIENT_ID') or os.getenv('bsnClientID')
    secret = os.getenv('BSN_SECRET') or os.getenv('bsnSecret')
    network = os.getenv('BSN_NETWORK') or os.getenv('bsnNetwork')
    
    if not all([client_id, secret, network]):
        raise ValueError(
            "BSN Cloud credentials not found. Please set credentials using:\n"
            "1. bsn_cloud_api.configure(client_id, secret, network), or\n"
            "2. Environment variables: BSN_CLIENT_ID, BSN_SECRET, BSN_NETWORK, or\n"
            "3. .env file with bsnClientID, bsnSecret, bsnNetwork"
        )
    
    return (client_id, secret, network)


def configure(client_id: str, secret: str, network: str):
    '''
    Configure BSN Cloud API credentials programmatically.
    
    This is an alternative to using environment variables or .env files.
    
    Args:
        client_id (str): Your BSN Cloud client ID
        secret (str): Your BSN Cloud client secret
        network (str): Your BSN Cloud network name
    
    Example:
        >>> import bsn_cloud_api
        >>> bsn_cloud_api.configure(
        ...     client_id="your_client_id",
        ...     secret="your_secret",
        ...     network="your_network"
        ... )
    '''
    global _configured_credentials
    _configured_credentials = (client_id, secret, network)


def login() -> Login:
    '''Logs in to the BSN Cloud API, retrieves a Bearer token and selects the appropriate network.'''
    safety_margin = 15 # seconds subtracted from the validity of the token to account for network delays
    creds = _load_credentials()
    # Get Bearer token
    url = 'https://auth.bsn.cloud/realms/bsncloud/protocol/openid-connect/token'
    body = {
        'grant_type': 'client_credentials'
    }
    request_datetime = datetime.datetime.now()
    try:
        response = requests.post(url, auth=(creds[0], creds[1]), data=body)
    except requests.RequestException as e:
        login_result = Login(
            success=False,
            error="Error authenticating",
            bearer=None,
            time_of_issue=request_datetime,
            expiration_time=0
        )
        return login_result
    if response.status_code != 200:
        login_result = Login(
            success=False,
            error="Error authenticating",
            bearer=None,
            time_of_issue=request_datetime,
            expiration_time=0
        )
        return login_result
    response_json = json.loads(response.text)
    token = response_json['access_token']
    bearer = "Bearer " + token

    # Select Network
    network = creds[2]
    body2 = {
    'name': network
    }
    headers2 = {
                "authorization": bearer,
                'Content-Type': 'application/json'
                }
    url2 = 'https://api.bsn.cloud/2022/06/REST/Self/Session/Network'
    try:
        response2 = requests.put(url=url2, headers=headers2, json=body2)
    except requests.RequestException as e:
        login_result = Login(
            success=False,
            error="Error selecting site",
            bearer=None,
            time_of_issue=request_datetime,
            expiration_time=0
        )
        return login_result

    if response2.status_code == 200 or response2.status_code == 204:
        login_result = Login(
            success=True,
            error=None,
            bearer=bearer,
            time_of_issue=request_datetime,
            expiration_time=response_json['expires_in'] - safety_margin
        )
        return login_result
    else:
        login_result = Login(
            success=False,
            error=response2.text,
            bearer=None,
            time_of_issue=request_datetime,
            expiration_time=0
        )
        return login_result
    

def _get_valid_login() -> Login:
    """Internal helper function. Retrieves a valid login session, logging in if necessary."""
    global _current_login

    if _current_login is None or not _current_login.success or not _current_login.is_valid():
        _current_login = login()

        if not _current_login.success:
            raise Exception(f"Login to BSN.cloud failed: {_current_login.error}")

    return _current_login

# ---------------------------------- BSN Cloud API ----------------------------------
# This section is very incomplete and only has a few functions
def get_devices(description: str | None = None) -> dict:
    """Gets a dict of devices from the BSN Cloud API."""
    url = 'https://api.bsn.cloud/2022/06/REST/Devices/'
    params = {}
    if description:
        filter_str = f"[Description] IS '*{description}*'"
        params['filter'] = filter_str
    params['sort'] = "[Settings].[Name] ASC"
    params['pageSize'] = "100"

    return _get_request(url=url, params=params)

def get_setups(page_number:int=1, page_size:int=100, network_name:str | None=None) -> dict:
    """Gets a dict of setups from the BSN Cloud API."""
    if network_name is None:
        network_name = os.getenv('bsnNetwork')
    url = f'https://provision.bsn.cloud/rest-setup/v3/setup/?page[pageNum]={page_number}&page[pageSize]={page_size}&sort[packageName]=1&query[networkName]={network_name}'
    return _get_request(url=url)

def update_setup(setup_object:str, username:str | None=None) -> dict:
    """Updates a setup in the BSN Cloud."""
    if username is None:
        username = os.getenv('bsnUser')
    url = f'https://provision.bsn.cloud/rest-setup/v3/setup?username={username}'
    
    return _put_request(url=url, raw_data=setup_object)

# Provisioning Endpoints
def get_provisioning_records(sort_serial:bool=True, page_number:int=1, page_size:int=100) -> dict:
    """
    Gets a dictionary of all provisioning records from the BSN Cloud API. Please note that this endpoint is paginated and this request needs to be repeated to get all records with continued page number.\n
    Args:
        sort_serial (bool): Whether to sort the records by serial number (default: True)\n
        page_number (int): The page number to retrieve (default: 1)\n
        page_size (int): The number of records per page (default: 100)
    """
    url = f'https://provision.bsn.cloud/rest-device/v2/device/'
    network = _load_credentials()[2]
    params = {
        "query[NetworkName]": network,
        "sort[SerialNumber]": "1" if sort_serial else "0",
        "page[pageNum]": str(page_number),
        "page[pageSize]": str(page_size)
    }
    return _get_request(url=url, params=params)

def get_provisioning_record(record_id:str | None=None, serial_number:str | None=None) -> dict:
    """Gets a single provisioning record by serial number from the BSN Cloud API.
    Args:
        record_id (str | None): The unique identifier of the device record to retrieve.
        serial_number (str | None): The serial number of the device to retrieve.
        
    If both record_id and serial_number are provided, record_id will be used.
    
    Returns:
        dict: The provisioning record data or an error dict.

    Raises:
    """
    if not record_id and not serial_number:
        raise ValueError("Either 'record_id' or 'serial_number' must be provided.")
    if record_id:
        params = {"_id": record_id}
    else:   
        params = {"serial": serial_number}
    url = f'https://provision.bsn.cloud/rest-device/v2/device/'
    return _get_request(url=url, params=params)

def create_provisioning_record(serial_number:str, username:str, name:str | None=None, description:str | None=None, setup_id:str | None=None, setup_name:str | None=None, url:str | None=None, model:str | None=None, userdata:str | None=None) -> dict:
    '''
    Creates a new provisioning record in the BSN Cloud API.
    
    Args:
        serial_number (str): The serial number of the device to provision.
        username (str): The login of the person who owns the record. 
            Note that the person may or may not be registered in BSN.Cloud.
        name (str, optional): The name of the device. If not provided, 
            the name provided in the referenced setup package will be used.
        description (str, optional): The description of the device. If not provided,
            the description provided in the referenced setup package will be used.
        setup_id (str, optional): The unique identifier of the setup package 
            stored in B-Deploy and managed using the PSS API.
        setup_name (str, optional): The descriptive name of a setup package 
            stored in B-Deploy and managed using the PSS API.
        url (str, optional): The URL from which the player will download 
            its presentation as part of the final provisioning step.
        model (str, optional): The model of the player. If not provided, 
            the model will be determined automatically based on the serial number.
        userdata (str, optional): Allows you to provide additional attributes 
            to a custom setup package.
    
    Returns:
        dict: Response from the BSN.cloud API or error dict.
    
    Raises:
        ValueError: If neither setup_id nor setup_name is provided.
    
    Example:
        >>> create_provisioning_record(
        ...     serial_number="ABC123",
        ...     username="admin",
        ...     setup_id="12345",
        ...     name="Lobby Display"
        ... )
    '''
    if not setup_id and not setup_name:
        raise ValueError(
            "Either 'setup_id' or 'setup_name' must be provided."
        )

    network = _load_credentials()[2]
    api_url = f'https://provision.bsn.cloud/rest-device/v2/device/'

    payload = {
        "username": username,
        "serial": serial_number,
        "NetworkName": network,
    }
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if setup_id:
        payload["setupId"] = setup_id
    if setup_name:
        payload["setupName"] = setup_name
    if url:
        payload["url"] = url
    if model:
        payload["model"] = model
    if userdata:
        payload["userdata"] = userdata

    return _post_request(url=api_url, payload=payload)

def update_provisioning_record(
    record_id: str,
    serial_number: str,
    username: str,
    name: str | None = None,
    description: str | None = None,
    setup_id: str | None = None,
    setup_name: str | None = None,
    url: str | None = None,
    model: str | None = None,
    userdata: str | None = None
) -> dict:
    '''
    Updates an existing provisioning record in the BSN Cloud API.
    
    Args:
        record_id (str): The unique identifier (a 24-digit hexadecimal number) 
            of the device object.
        serial_number (str): The serial number of the device to provision.
        username (str): The login of the person who owns the record. 
            Note that the person may or may not be registered in BSN.Cloud.
        name (str, optional): The name of the device. If not provided, 
            the name provided in the referenced setup package will be used.
        description (str, optional): The description of the device. If not provided,
            the description provided in the referenced setup package will be used.
        setup_id (str, optional): The unique identifier of the setup package 
            stored in B-Deploy and managed using the PSS API.
        setup_name (str, optional): The descriptive name of a setup package 
            stored in B-Deploy and managed using the PSS API.
        url (str, optional): The URL from which the player will download 
            its presentation as part of the final provisioning step.
        model (str, optional): The model of the player. If not provided, 
            the model will be determined automatically based on the serial number.
        userdata (str, optional): Allows you to provide additional attributes 
            to a custom setup package.
    
    Returns:
        dict: Response from the BSN.cloud API or error dict.
    
    Raises:
        ValueError: If neither setup_id nor setup_name is provided.
    
    Example:
        >>> update_provisioning_record(
        ...     record_id="507f1f77bcf86cd799439011",
        ...     serial_number="ABC123",
        ...     username="admin",
        ...     setup_id="12345",
        ...     name="Updated Lobby Display"
        ... )
    '''
    # Validate that at least one setup reference is provided
    if not setup_id and not setup_name:
        raise ValueError(
            "Either 'setup_id' or 'setup_name' must be provided."
        )
    
    # Get network from credentials
    network = _load_credentials()[2]
    
    # Build API endpoint URL (renamed to avoid collision with 'url' parameter)
    api_url = 'https://provision.bsn.cloud/rest-device/v2/device/'
    
    # Build payload
    payload = {
        "_id": record_id,
        "username": username,
        "serial": serial_number,
        "NetworkName": network,
    }
    
    # Add optional parameters if provided
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if setup_id is not None:
        payload["setupId"] = setup_id
    if setup_name is not None:
        payload["setupName"] = setup_name
    if url is not None:  # Now correctly checks the parameter, not the API URL
        payload["url"] = url
    if model is not None:
        payload["model"] = model
    if userdata is not None:
        payload["userdata"] = userdata
    
    return _put_request(url=api_url, params={"_id": record_id}, payload=payload)

def delete_provisioning_record(record_id: str | None=None, serial_number: str | None=None) -> dict:
    '''Deletes a provisioning record from BSN Cloud by either record_id or serial_number
    Args:
        record_id (str | None): The unique identifier of the device record to delete.
        serial_number (str | None): The serial number of the device to delete.

    If both record_id and serial_number are provided, record_id will be used.
        
    Returns:
        dict: Response from the BSN.cloud API or error dict.
    
    Raises: ValueError if neither record_id nor serial_number is provided. '''
    if not record_id and not serial_number:
        raise ValueError("Either 'record_id' or 'serial_number' must be provided.")

    api_url = 'https://provision.bsn.cloud/rest-device/v2/device/'

    if record_id:
        params = {"_id": record_id}
    else:
        params = {"serial": serial_number}

    return _delete_request(url=api_url, params=params)

def delete_provisioning_records(ids: list[str]) -> dict:
    '''Deletes multiple provisioning records from BSN Cloud by their IDs
    Args:
        ids (list[str]): The list of unique identifiers of the device records to delete.

    Returns:
        dict: Response from the BSN.cloud API or error dict.'''

    if len(ids) == 0:
        raise ValueError("The list of IDs must not be empty.")

    api_url = 'https://provision.bsn.cloud/rest-device/v2/device/'

    params = {"_ids": ids}

    return _delete_request(url=api_url, params=params)


# ---------------------------------- Remote DWS API ----------------------------------
# This section uses the Remote DWS endpoints and is intended to include all endpoints, but is currently not complete. 

# Information Endpoints
def get_device_info(serial_number:str) -> dict:
    '''Retrieves general information about the player by its serial number using the Remote DWS and not BSN Cloud devices Endpoint'''
    url = "https://ws.bsn.cloud/rest/v1/info/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _get_request(url=url, params=params)
    

def get_device_time(serial_number:str) -> dict:
    '''Retrieves the date and time as configured on the player. The date/time value is formatted as "yyyy-mm-dd hh:mm:ss <timezone>".'''
    url = f"https://ws.bsn.cloud/rest/v1/time/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _get_request(url=url, params=params)


def put_device_time(serial_number:str, time:str, date:str, applyTimeZone:bool) -> dict:
    '''Sets the date/time on the player\n
    time:str The time to set on the player, formatted as "hh:mm:ss <timezone>" (timezone is optional)\n
    date:str The date to set on the player, formatted as "yyyy-mm-dd"\n
    applyTimeZone:bool A flag specifying whether the date and time should be applied using the time zone configured on the player (True) or the UTC time zone (False)
    '''
    is_valid, error = validate_time_date(time, date)
    if not is_valid:
        raise ValueError(error)
    url = f"https://ws.bsn.cloud/rest/v1/time/"
    
    body = {
        "data": {
            "time": time,
            "date": date,
            "applyTimezone": applyTimeZone
        }
    }

    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _put_request(url=url, params=params, payload=body)


def get_device_health(serial_number:str) -> dict:
    '''Retrieves the current status of the player. Currently, this endpoint is only used to determine if a player can respond to a WebSockets request; it cannot determine the error state of a player.'''
    url = f"https://ws.bsn.cloud/rest/v1/health/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _get_request(url=url, params=params)
    
# Logs Endpoints  
def get_device_logs(serial_number:str) -> dict:
    '''Get device logs by its serial number using the Remote DWS'''
    url = f"https://ws.bsn.cloud/rest/v1/logs/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _get_request(url=url, params=params)


def get_device_crash_dumps(serial_number:str) -> dict:
    '''Retrieves the crash dump from the player'''
    url = f"https://ws.bsn.cloud/rest/v1/crash-dump/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _get_request(url=url, params=params)

# Control Endpoints
def put_device_reboot(serial_number: str, mode: str | None = None) -> dict:
    '''Reboots the player. The player will not send a response to a reboot request.
        
    Args:
        serial_number (str): The serial number of the player
        mode (str, optional): Reboot mode. Valid values:
            - "crash_report": Reboot with crash report
            - "factory_reset": Factory reset the player
            - "disable_autorun": Reboot with autorun disabled
            - None: Standard reboot (default)

    Returns:
        dict: Response from the API or error dict

    Raises:
        ValueError: If mode is not a valid option
    '''
    url = "https://ws.bsn.cloud/rest/v1/control/reboot/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    if mode is None:
        payload = None
    else:
        mode_payloads = {
            "crash_report": {"crash_report": True},
            "factory_reset": {"factory_reset": True},
            "disable_autorun": {"autorun": "disable"}
        }
        
        if mode not in mode_payloads:
            raise ValueError(
                f"Invalid mode: '{mode}'. Must be one of: "
                f"{', '.join(mode_payloads.keys())}, or None"
            )
        
        payload = {"data": mode_payloads[mode]}
    
    return _put_request(url=url, params=params, payload=payload)


def get_device_password(serial_number:str) -> dict:
    '''Retrieves information about the current password of the local DWS (but not the password itself) such as whether the password is blank or invalid'''
    url = f"https://ws.bsn.cloud/rest/v1/control/dws-password/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    return _get_request(url=url, params=params)


def put_device_password(serial_number:str, password:str, previous_password:str) -> dict:
    '''
    Sets a new password for the local DWS (or removes the password requirement on older BOS versions).
    
    Args:
        serial_number (str): The serial number of the player
        password (str): The new password to set. This API enforces strong password requirements, so passing in an empty string will cause an error.
        previous_password (str): The current password (required for authentication). This value can be an empty string to indicate that the previous password was blank.
    '''
    url = f"https://ws.bsn.cloud/rest/v1/control/dws-password/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    payload = {
        "data": {
            "password": password,
            "previousPassword": previous_password
        }
    }
    return _put_request(url=url, params=params, payload=payload)


def get_device_local_dws_status(serial_number: str) -> dict:
    '''
    Retrieves the current state of the local DWS (Diagnostic Web Server).
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Local DWS status indicating if it's enabled or disabled.
    
    Example:
        >>> status = get_device_local_dws_status("ABC123")
        >>> if status['data']['result']['value']:
        ...     print("Local DWS is enabled")
        ... else:
        ...     print("Local DWS is disabled")
    '''
    url = "https://ws.bsn.cloud/rest/v1/control/local-dws/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_device_local_dws(serial_number: str, enable: bool) -> dict:
    '''
    Enables or disables the local DWS (Diagnostic Web Server) on the player.
    This will typically cause the player to reboot.
    
    Args:
        serial_number (str): The serial number of the target player.
        enable (bool): True to enable local DWS, False to disable it.
    
    Returns:
        dict: Response indicating success and whether player will reboot.
    
    Example:
        >>> # Enable local DWS
        >>> result = set_device_local_dws("ABC123", enable=True)
        >>> if result['data']['result']['reboot']:
        ...     print("Player is rebooting to enable local DWS")
        
        >>> # Disable local DWS
        >>> set_device_local_dws("ABC123", enable=False)
    '''
    url = "https://ws.bsn.cloud/rest/v1/control/local-dws/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "enable": enable
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def reset_device_ssh_host_keys(serial_number: str, reboot: bool | None =None) -> dict:
    '''
    Resets the SSH host keys by regenerating new host key pairs.
    
    This is useful for security purposes or when host keys have been compromised.
    The system will automatically determine if a reboot is required, unless 
    overridden by the reboot parameter.
    
    Args:
        serial_number (str): The serial number of the target player.
        reboot (bool, optional): Force reboot (True) or prevent reboot (False). 
            If None, system decides automatically.
    
    Returns:
        dict: Response indicating success.
    
    Example:
        >>> # Reset SSH host keys (system decides on reboot)
        >>> reset_device_ssh_host_keys("ABC123")
        
        >>> # Reset and force reboot
        >>> reset_device_ssh_host_keys("ABC123", reboot=True)
    '''
    url = "https://ws.bsn.cloud/rest/v1/control/ssh-host-keys/reset/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = None
    if reboot is not None:
        payload = {
            "data": {
                "reboot": str(reboot).lower()
            }
        }
    
    return _put_request(url=url, params=params, payload=payload)


def reset_device_dws_default_certs(serial_number: str, reboot: bool | None = None) -> dict:
    '''
    Resets the DWS default certificates by regenerating new certificate pairs.
    
    This is useful for security purposes or when certificates have been compromised.
    The system will reboot to activate new certificates, unless overridden by 
    the reboot parameter.
    
    Args:
        serial_number (str): The serial number of the target player.
        reboot (bool, optional): Force reboot (True) or prevent reboot (False). 
            If None, system decides automatically (typically reboots).
    
    Returns:
        dict: Response indicating success.
    
    Example:
        >>> # Reset DWS certificates (will typically reboot)
        >>> reset_device_dws_default_certs("ABC123")
        
        >>> # Reset without forcing reboot
        >>> reset_device_dws_default_certs("ABC123", reboot=False)
    '''
    url = "https://ws.bsn.cloud/rest/v1/control/dws-default-certs/reset/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = None
    if reboot is not None:
        payload = {
            "data": {
                "reboot": str(reboot).lower()
            }
        }
    
    return _put_request(url=url, params=params, payload=payload)

# Storage Endpoints
def get_device_files(serial_number:str, storage_type:str="sd", path:str | None=None, raw:bool=False, contents:bool=False) -> dict:
    '''
    Retrieves information about the storage devices on the player.

    Args:
        serial_number (str): The serial number of the player.
        storage_type (str): The type of storage medium to query (default: "sd") (valid values: "sd", "usb", "ssd").
        path (str, optional): The specific file path to query.
        raw (bool, optional): Returns the raw contents of a directory.(default: False)
        contents (bool): If a file is specified, returns the contents of that file (default: False)
    
    Returns:
        dict: Response from the API or error dict
    
    Raises:
        ValueError: If storage_type is not valid
    '''
    valid_storage_types = ["sd", "usb", "ssd"]
    if storage_type not in valid_storage_types:
        raise ValueError(
            f"Invalid storage_type: '{storage_type}'. "
            f"Must be one of: {', '.join(valid_storage_types)}"
        )
    if raw and contents:
        raise ValueError("Cannot specify both 'raw' and 'contents' parameters")
    
    url = f"https://ws.bsn.cloud/rest/v1/files/{storage_type}/"
    if path:
        url += path.lstrip('/')
    params: dict[str, str | bool] = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    if raw:
        params['raw'] = True
    if contents:
        params['contents'] = True
    return _get_request(url=url, params=params)


def put_device_files(serial_number: str, local_file_path: str, storage_type: str = "sd", 
                     file_path: str | None = None, dest_filename: str | None = None, 
                     file_type: str | None = None) -> dict:
    '''
    Uploads a file to a BrightSign player's storage via BSN.cloud API.
    
    This function reads a local file and uploads it to the specified storage medium
    on a BrightSign player. The MIME type is automatically detected from the file
    extension unless explicitly provided.
    
    Args:
        serial_number (str): The serial number of the target player.
        local_file_path (str): Path to the local file to be uploaded.
        storage_type (str, optional): The storage medium on the player. 
            Valid values: "sd", "usb", "ssd". Defaults to "sd".
        file_path (str, optional): The destination directory path on the player's storage.
            If None, uploads to root directory.
        dest_filename (str, optional): The filename to use on the player. 
            If None, uses the original filename from local_file_path.
        file_type (str, optional): MIME type of the file (e.g., "video/mp4", "image/jpeg").
            If None, automatically detected from file extension.
    
    Returns:
        dict: Response from the BSN.cloud API or error dict.
    
    Raises:
        ValueError: If storage_type is not one of the valid options.
        FileNotFoundError: If the specified local_file_path does not exist.
    
    Example:
        >>> # Upload a video file
        >>> response = put_device_files("ABC123456", "/local/path/video.mp4")
        
        >>> # Upload to specific path with custom filename
        >>> response = put_device_files(
        ...     serial_number="ABC123456",
        ...     local_file_path="/local/path/video.mp4",
        ...     storage_type="sd",
        ...     file_path="media/videos",
        ...     dest_filename="intro.mp4"
        ... )
    '''
    # Validate storage type
    valid_storage_types = ["sd", "usb", "ssd"]
    if storage_type not in valid_storage_types:
        raise ValueError(
            f"Invalid storage_type: '{storage_type}'. "
            f"Must be one of: {', '.join(valid_storage_types)}"
        )
    
    # Check if file exists
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"File not found: '{local_file_path}'")
    
    # Determine filename to use on destination
    file_name = dest_filename or os.path.basename(local_file_path)
    
    # Auto-detect MIME type if not provided
    if file_type is None:
        file_type, _ = mimetypes.guess_type(local_file_path)
        if file_type is None:
            file_type = 'application/octet-stream'  # Default fallback for unknown types
    
    # Determine if file should be sent as plain text or base64 encoded
    text_extensions = ['brs', 'json', 'js', 'xml', 'rtf']
    file_extension = os.path.splitext(local_file_path)[1].lstrip('.')
    is_text_file = (
        file_type.startswith('text/') or 
        file_extension in text_extensions
    )
    
    # Read and encode file contents based on type
    if is_text_file:
        # Plain text encoding for text files
        with open(local_file_path, 'r', encoding='utf-8') as f:
            file_contents = f.read()
    else:
        # Base64 data URL encoding for binary files (images, videos, zip, etc.)
        with open(local_file_path, 'rb') as f:
            binary_data = f.read()
        base64_data = base64.b64encode(binary_data).decode('ascii')
        file_contents = f"data:{file_type};base64,{base64_data}"
    
    # Build the API URL
    url = f"https://ws.bsn.cloud/rest/v1/files/{storage_type}/"
    if file_path:
        url += file_path.lstrip('/') + '/'
    
    # API parameters
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    # Construct the upload path for the payload
    upload_path = f"/{storage_type}"
    if file_path:
        upload_path += f"/{file_path.lstrip('/')}"
    
    # Payload with file data - following BSN.cloud API structure
    payload = {
        "data": {
            "fileUploadPath": upload_path,
            "files": [
                {
                    "fileName": file_name,
                    "fileContents": file_contents,
                    "fileType": file_type
                }
            ]
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def create_device_directory(serial_number: str, dir_path: str, storage_type: str = "sd") -> dict:
    '''
    Creates a directory on a BrightSign player's storage.
    
    Args:
        serial_number (str): The serial number of the target player.
        dir_path (str): The directory path to create (e.g., "myfolder" or "media/videos").
        storage_type (str, optional): The storage medium. Valid values: "sd", "usb", "ssd". 
            Defaults to "sd".
    
    Returns:
        dict: Response from the BSN.cloud API.
    
    Example:
        >>> create_device_directory("ABC123", "media/videos", "sd")
    '''
    valid_storage_types = ["sd", "usb", "ssd"]
    if storage_type not in valid_storage_types:
        raise ValueError(
            f"Invalid storage_type: '{storage_type}'. "
            f"Must be one of: {', '.join(valid_storage_types)}"
        )
    
    url = f"https://ws.bsn.cloud/rest/v1/files/{storage_type}/{dir_path.lstrip('/')}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _put_request(url=url, params=params, payload=None)


def rename_device_file(serial_number: str, path: str, new_name: str, storage_type: str = "sd") -> dict:
    '''
    Renames a file on a BrightSign player's storage.
    
    Args:
        serial_number (str): The serial number of the target player.
        path (str): The current path of the file to rename (e.g., "media/myfile.txt").
        new_name (str): The new filename (not a path, just the filename).
        storage_type (str, optional): The storage medium. Valid values: "sd", "usb", "ssd". 
            Defaults to "sd".
    
    Returns:
        dict: Response from the BSN.cloud API.
    
    Raises:
        ValueError: If storage_type is invalid or new_name contains path separators.
    
    Example:
        >>> rename_device_file("ABC123", "media/myfile.txt", "newfile.txt")
        >>> rename_device_file("ABC123", "test.brs", "autorun.brs", storage_type="sd")
    '''
    valid_storage_types = ["sd", "usb", "ssd"]
    if storage_type not in valid_storage_types:
        raise ValueError(
            f"Invalid storage_type: '{storage_type}'. "
            f"Must be one of: {', '.join(valid_storage_types)}"
        )
    
    # Validate new_name is just a filename, not a path
    if '/' in new_name or '\\' in new_name:
        raise ValueError(
            f"new_name should be a filename only, not a path. "
            f"Got: '{new_name}'"
        )
    
    url = f"https://ws.bsn.cloud/rest/v1/files/{storage_type}/{path.lstrip('/')}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number,
    }
    
    payload = {
        "data": {
            "name": new_name
        }
    }   
    
    return _post_request(url=url, params=params, payload=payload)


def delete_device_file(serial_number: str, path: str, storage_type: str = "sd") -> dict:
    '''
    Deletes a file from a BrightSign player's storage.
    
    Args:
        serial_number (str): The serial number of the target player.
        path (str): The path of the file to delete (e.g., "media/myfile.txt").
        storage_type (str, optional): The storage medium. Valid values: "sd", "usb", "ssd". 
            Defaults to "sd".
    
    Returns:
        dict: Response from the BSN.cloud API.
    
    Raises:
        ValueError: If storage_type is not one of the valid options.
    
    Example:
        >>> delete_device_file("ABC123", "media/oldfile.txt")
        >>> delete_device_file("ABC123", "autorun.brs", storage_type="sd")
    '''
    valid_storage_types = ["sd", "usb", "ssd"]
    if storage_type not in valid_storage_types:
        raise ValueError(
            f"Invalid storage_type: '{storage_type}'. "
            f"Must be one of: {', '.join(valid_storage_types)}"
        )
    
    url = f"https://ws.bsn.cloud/rest/v1/files/{storage_type}/{path.lstrip('/')}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _delete_request(url=url, params=params)

# Diagnostic Endpoints
def get_device_diagnostics(serial_number: str) -> dict:
    '''
    Runs network diagnostics on the player including ethernet, wifi, modem, and internet tests.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Diagnostic results containing ethernet, wifi, modem, and internet test results.
    
    Example:
        >>> diagnostics = get_device_diagnostics("ABC123")
        >>> if diagnostics['data']['result']['ethernet']['ok']:
        ...     print("Ethernet is working")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_dns_lookup(serial_number: str, domain_name: str) -> dict:
    '''
    Tests DNS name resolution on the player for a specified domain.
    
    Args:
        serial_number (str): The serial number of the target player.
        domain_name (str): The DNS address to look up (e.g., "google.com").
    
    Returns:
        dict: DNS lookup results including IPv4, IPv6, MX records, and server test results.
    
    Example:
        >>> result = get_device_dns_lookup("ABC123", "google.com")
        >>> ipv4_addresses = result['data']['result']['records']['ipv4']
    '''
    url = f"https://ws.bsn.cloud/rest/v1/diagnostics/dns-lookup/{domain_name}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_ping(serial_number: str, domain_name: str) -> dict:
    '''
    Requests the player to ping a specified IP or DNS address on its local network.
    Note: This call can take over 10 seconds to return.
    
    Args:
        serial_number (str): The serial number of the target player.
        domain_name (str): The IP or DNS address to ping (e.g., "8.8.8.8" or "google.com").
    
    Returns:
        dict: Ping results including packets transmitted/received and timing statistics.
    
    Example:
        >>> result = get_device_ping("ABC123", "8.8.8.8")
        >>> packets_received = result['data']['result']['response']['results']['ipv4'][0]['results']['received']
    '''
    url = f"https://ws.bsn.cloud/rest/v1/diagnostics/ping/{domain_name}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_traceroute(serial_number: str, domain_name: str, resolve_address: bool = True) -> dict:
    '''
    Performs a traceroute diagnostic on the player to a specified IP or DNS address.
    Note: This call can take several minutes to return.
    
    Args:
        serial_number (str): The serial number of the target player.
        domain_name (str): The IP or DNS address to trace (e.g., "8.8.8.8" or "google.com").
        resolve_address (bool, optional): Whether to resolve hostnames. Defaults to True.
    
    Returns:
        dict: Traceroute results including hop-by-hop route information.
    
    Example:
        >>> result = get_device_traceroute("ABC123", "google.com")
        >>> route = result['data']['result']['results'][domain_name]['route']
    '''
    url = f"https://ws.bsn.cloud/rest/v1/diagnostics/trace-route/{domain_name}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number,
        "resolveAddress": str(resolve_address).lower()
    }
    
    return _get_request(url=url, params=params)


def get_device_network_config(serial_number: str, interface: str = "eth0") -> dict:
    '''
    Retrieves network interface configuration information from the player.
    
    Args:
        serial_number (str): The serial number of the target player.
        interface (str, optional): The network interface name. 
            Valid values: "eth0", "wlan0", "modem". Defaults to "eth0".
    
    Returns:
        dict: Network configuration including IP addresses, DNS servers, gateway, and other settings.
    
    Example:
        >>> config = get_device_network_config("ABC123", "eth0")
        >>> ip_address = config['data']['result']['response'][1]['ipaddresslist']
    '''
    url = f"https://ws.bsn.cloud/rest/v1/diagnostics/network-configuration/{interface}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def put_device_network_config(serial_number: str, interface: str, config: dict) -> dict:
    '''
    Applies a test network configuration on the player. You should use GET to get the configuration parameters before setting it using this API. The text and output parameters are NOT needed in PUT.
    
    Args:
        serial_number (str): The serial number of the target player.
        interface (str): The network interface name (e.g., "eth0", "wlan0", "modem").
        config (dict): Network configuration dictionary with keys like:
            - caCertificates (str): CA certificate file contents
            - clientCertificate (bool): Whether using client certificate
            - clientIdentifier (str): DHCP client identifier
            - dnsServerList (list): List of DNS server IP addresses
            - domain (str): Domain name
            - enabledProtocolList (list): List of enabled protocols (e.g., ["ipv4", "ipv6"])
            - ipAddressList (list): List of IP addresses
            - metric (int): Routing metric
            - and other network parameters
    
    Returns:
        dict: Response from the BSN.cloud API.
    
    Example:
        >>> config = {
        ...     "clientIdentifier": "brightsign-ABC123",
        ...     "enabledProtocolList": ["ipv4", "ipv6"],
        ...     "dnsServerList": []
        ... }
        >>> put_device_network_config("ABC123", "eth0", config)
    '''
    url = f"https://ws.bsn.cloud/rest/v1/diagnostics/network-configuration/{interface}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": config
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_device_network_neighborhood(serial_number: str) -> dict:
    '''
    Retrieves information about other BrightSign players on the same network.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: List of neighboring players with their chassis info, IP addresses, and ports.
    
    Example:
        >>> neighbors = get_device_network_neighborhood("ABC123")
        >>> for player in neighbors['data']['result']['response']:
        ...     print(f"Found player: {player['chassis_name']}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/network-neighborhood/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_packet_capture_status(serial_number: str) -> dict:
    '''
    Gets the current status of packet capture operation on the player.
    Note: Requires legacy DWS to be working.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Status including whether packet capture is running.
    
    Example:
        >>> status = get_device_packet_capture_status("ABC123")
        >>> is_running = status['data']['result']['is_running']
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/packet-capture/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def start_device_packet_capture(serial_number: str, filename: str = "capture.pcap", 
                                interface: str = "eth0", duration: int = 300, 
                                max_packets: int = 0, snaplen: int = 0, 
                                filter_expr: str = "") -> dict:
    '''
    Starts a packet capture operation on the player.
    
    Args:
        serial_number (str): The serial number of the target player.
        filename (str, optional): Name of the capture file. Defaults to "capture.pcap".
        interface (str, optional): Network interface to capture. Defaults to "eth0".
        duration (int, optional): Capture duration in seconds. Defaults to 300 (5 minutes).
        max_packets (int, optional): Maximum packets to capture. 0 = unlimited. Defaults to 0.
        snaplen (int, optional): Maximum packet size. 0 = capture entire packet. Defaults to 0.
        filter_expr (str, optional): Packet filter using pcap syntax. Defaults to "" (no filter).
    
    Returns:
        dict: Response indicating if capture started successfully.
    
    Example:
        >>> start_device_packet_capture("ABC123", duration=60, filter_expr="port 80")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/packet-capture/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "filename": filename,
            "interface": interface,
            "duration": duration,
            "maxPackets": max_packets,
            "snaplen": snaplen,
            "filter": filter_expr
        }
    }
    
    return _post_request(url=url, params=params, payload=payload)


def stop_device_packet_capture(serial_number: str) -> dict:
    '''
    Stops a running packet capture operation on the player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Response indicating if capture stopped successfully.
    
    Example:
        >>> stop_device_packet_capture("ABC123")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/packet-capture/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _delete_request(url=url, params=params)


def get_device_telnet_status(serial_number: str) -> dict:
    '''
    Gets information about telnet configuration on the player.
    Note: Only available in BOS 9.0.110 and above.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Telnet configuration including enabled status and port number.
    
    Example:
        >>> status = get_device_telnet_status("ABC123")
        >>> if status['data']['result']['enabled']:
        ...     print(f"Telnet is enabled on port {status['data']['result']['portnumber']}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/telnet/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def put_device_telnet_config(serial_number: str, enabled: bool, port_number: int = 23, 
                             password: str | None = None, reboot: bool = True) -> dict:
    '''
    Configures telnet settings on the player.
    Note: Only available in BOS 9.0.110 and above.
    
    Args:
        serial_number (str): The serial number of the target player.
        enabled (bool): Enable or disable telnet.
        port_number (int, optional): Port number for telnet. Defaults to 23.
        password (str, optional): Plain text login password for telnet connection.
        reboot (bool, optional): Reboot player immediately after applying. Defaults to True.
    
    Returns:
        dict: Response indicating if configuration was successful.
    
    Example:
        >>> put_device_telnet_config("ABC123", enabled=True, password="mypassword")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/telnet/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "enabled": enabled,
            "portnumber": port_number,
            "reboot": reboot
        }
    }
    
    if password is not None:
        payload["data"]["password"] = password
    
    return _put_request(url=url, params=params, payload=payload)


def get_device_ssh_status(serial_number: str) -> dict:
    '''
    Gets information about SSH configuration on the player.
    Note: Only available in BOS 9.0.110 and above.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: SSH configuration including enabled status, port number, and password status.
    
    Example:
        >>> status = get_device_ssh_status("ABC123")
        >>> if status['data']['result']['enabled']:
        ...     print(f"SSH is enabled on port {status['data']['result']['portnumber']}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/ssh/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def put_device_ssh_config(serial_number: str, enabled: bool, port_number: int = 22, 
                         password: str | None = None, obfuscated_password: str | None = None, 
                         reboot: bool = True) -> dict:
    '''
    Configures SSH settings on the player.
    Note: Only available in BOS 9.0.110 and above.
    
    Args:
        serial_number (str): The serial number of the target player.
        enabled (bool): Enable or disable SSH.
        port_number (int, optional): Port number for SSH. Defaults to 22.
        password (str, optional): Plain text login password for SSH connection.
        obfuscated_password (str, optional): Obfuscated password (contact support@brightsign.biz 
            to learn about generating obfuscation keys).
        reboot (bool, optional): Reboot player immediately after applying. Defaults to True.
    
    Returns:
        dict: Response indicating if configuration was successful.
    
    Raises:
        ValueError: If both password and obfuscated_password are provided.
    
    Example:
        >>> put_device_ssh_config("ABC123", enabled=True, password="mypassword")
    '''
    if password is not None and obfuscated_password is not None:
        raise ValueError("Cannot specify both password and obfuscated_password")
    
    url = "https://ws.bsn.cloud/rest/v1/diagnostics/ssh/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "enabled": enabled,
            "portnumber": port_number,
            "reboot": reboot
        }
    }
    
    if password is not None:
        payload["data"]["password"] = password
    elif obfuscated_password is not None:
        payload["data"]["obfuscatedPassword"] = obfuscated_password
    
    return _put_request(url=url, params=params, payload=payload)

# Other Endpoints
def reformat_device_storage(serial_number: str, device_name: str = "sd", filesystem: str = "exfat") -> dict:
    '''
    Reformats the specified storage device on the player.
    WARNING: This will delete all data on the storage device.
    Note: You must disable autorun before reformatting the SD card.
    
    Args:
        serial_number (str): The serial number of the target player.
        device_name (str, optional): The storage device to reformat. 
            Valid values: "sd", "usb", "ssd". Defaults to "sd".
        filesystem (str, optional): The filesystem type to use. Defaults to "exfat".
    
    Returns:
        dict: Response indicating if the format was successful.
    
    Raises:
        ValueError: If device_name is not valid.
    
    Example:
        >>> # First disable autorun, then reformat
        >>> reformat_device_storage("ABC123", "sd", "exfat")
    '''
    valid_devices = ["sd", "usb", "ssd"]
    if device_name not in valid_devices:
        raise ValueError(
            f"Invalid device_name: '{device_name}'. "
            f"Must be one of: {', '.join(valid_devices)}"
        )
    
    url = f"https://ws.bsn.cloud/rest/v1/storage/{device_name}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "fs": filesystem
        }
    }
    
    return _delete_request(url=url, params=params, payload=payload)


def reprovision_device(serial_number: str) -> dict:
    '''
    Re-provisions the player by downloading its B-Deploy/provisioning setup and going through setup again.
    
    This will:
    1. Keep some setup-related registry keys
    2. Delete other registry entries
    3. Remove all files from the default storage device
    4. Reboot and fetch the setup package from B-Deploy
    5. Re-provision the player
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Response indicating if re-provisioning was initiated successfully.
    
    Example:
        >>> result = reprovision_device("ABC123")
        >>> if result['data']['result']['success']:
        ...     print("Player will re-provision and reboot")
    '''
    url = "https://ws.bsn.cloud/rest/v1/re-provision/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def take_device_snapshot(serial_number: str) -> dict:
    '''
    Takes a screenshot of the current screen contents and saves it to storage.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Response containing:
            - remoteSnapshotThumbnail: Base64 encoded thumbnail image
            - filename: Path to the full resolution image on the device
            - timestamp: When the snapshot was taken
            - devicename: Name of the device
            - width: Image width in pixels
            - height: Image height in pixels
    
    Example:
        >>> snapshot = take_device_snapshot("ABC123")
        >>> thumbnail_base64 = snapshot['data']['result']['remoteSnapshotThumbnail']
        >>> full_image_path = snapshot['data']['result']['filename']
        >>> # Use get_device_files() to retrieve the full resolution image
    '''
    url = "https://ws.bsn.cloud/rest/v1/snapshot/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _post_request(url=url, params=params, payload=None)


def send_device_custom_command(serial_number: str, command: str, return_immediately: bool = True) -> dict:
    '''
    Sends custom data to the player via UDP port 5000.
    
    The player sends the data as a JSON string message on UDP port 5000, which can be captured 
    by the autorun.brs or a JavaScript application on the player.
    
    Args:
        serial_number (str): The serial number of the target player.
        command (str): The custom data/command to send.
        return_immediately (bool, optional): If True, server responds immediately. 
            If False, server waits for a response from the player's UDP port 5000. 
            Defaults to True.
    
    Returns:
        dict: If return_immediately is True, returns success/error immediately.
              If False, returns the response from the player application.
    
    Example:
        >>> # Send a command and return immediately
        >>> send_device_custom_command("ABC123", "next", return_immediately=True)
        
        >>> # Send a command and wait for player response
        >>> response = send_device_custom_command("ABC123", "get_status", return_immediately=False)
    '''
    url = "https://ws.bsn.cloud/rest/v1/custom/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "command": command,
            "returnImmediately": return_immediately
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def download_device_firmware(serial_number: str, firmware_url: str) -> dict:
    '''
    Instructs the player to download and apply a firmware update from a public URL.
    
    Args:
        serial_number (str): The serial number of the target player.
        firmware_url (str): The public URL for downloading the firmware update file 
            (e.g., "https://bsncloud.s3.amazonaws.com/public/cobra-9.0.110-update.bsfw").
    
    Returns:
        dict: Response indicating if download was successful and if player will reboot.
    
    Example:
        >>> url = "https://bsncloud.s3.amazonaws.com/public/cobra-9.0.110-update.bsfw"
        >>> result = download_device_firmware("ABC123", url)
        >>> if result['data']['result']['success']:
        ...     print(f"Firmware downloading, player will reboot: {result['data']['result']['reboot']}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/download-firmware/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number,
        "url": firmware_url
    }
    
    return _get_request(url=url, params=params)

# Video Endpoints
def get_device_video_mode(serial_number: str) -> dict:
    '''
    Retrieves the currently active video mode on the player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Video mode information including width, height, framerate, scan method, 
              color depth, color space, and other display properties.
    
    Example:
        >>> mode = get_device_video_mode("ABC123")
        >>> print(f"Current mode: {mode['data']['result']['name']}")
        >>> print(f"Resolution: {mode['data']['result']['width']}x{mode['data']['result']['height']}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/video-mode/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_video_output(serial_number: str, connector: str = "hdmi", device: int = 0) -> dict:
    '''
    Retrieves comprehensive information about the specified video output including EDID,
    available modes, active/configured modes, power status, and audio information.
    
    Args:
        serial_number (str): The serial number of the target player.
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. 0 for single-output players, 
            0-3 for XC4055, 0-1 for XC2055/XT2145. Defaults to 0.
    
    Returns:
        dict: Comprehensive video output information including EDID, modes, resolution,
              audio format, power status, and HDCP status.
    
    Example:
        >>> output = get_device_video_output("ABC123")
        >>> if output['data']['result']['attached']['result']:
        ...     print("Display is connected")
        >>> best_mode = output['data']['result']['bestmode']['result']
    '''
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_video_edid(serial_number: str, connector: str = "hdmi", device: int = 0) -> dict:
    '''
    Returns the EDID (Extended Display Identification Data) string from the connected monitor/TV.
    
    Args:
        serial_number (str): The serial number of the target player.
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. Defaults to 0.
    
    Returns:
        dict: EDID information string from the connected display.
    
    Example:
        >>> edid = get_device_video_edid("ABC123")
        >>> edid_string = edid['data']['result']
    '''
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/edid/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_video_power_save(serial_number: str, connector: str = "hdmi", device: int = 0) -> dict:
    '''
    Retrieves the power status of the monitor connected to the player (as reported over EDID).
    
    Args:
        serial_number (str): The serial number of the target player.
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. Defaults to 0.
    
    Returns:
        dict: Power status information including:
            - is_connected: Whether monitor is connected
            - is_powered: Whether monitor is on (RX powered)
            - enabled: Whether power save mode is enabled
    
    Example:
        >>> status = get_device_video_power_save("ABC123")
        >>> if status['data']['result']['is_powered']:
        ...     print("Monitor is powered on")
    '''
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/power-save/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_device_video_power_save(serial_number: str, enabled: bool, 
                                connector: str = "hdmi", device: int = 0) -> dict:
    '''
    Enables or disables power save mode on the connected monitor via HDMI/VGA/Component.
    
    Args:
        serial_number (str): The serial number of the target player.
        enabled (bool): Whether to enable (True) or disable (False) power save mode.
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. Defaults to 0.
    
    Returns:
        dict: Response indicating if power save was enabled/disabled successfully.
    
    Example:
        >>> # Turn off the display
        >>> set_device_video_power_save("ABC123", enabled=True)
        
        >>> # Turn on the display
        >>> set_device_video_power_save("ABC123", enabled=False)
    '''
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/power-save/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "enabled": enabled
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_device_video_modes(serial_number: str, connector: str = "hdmi", device: int = 0) -> dict:
    '''
    Retrieves all available video modes on the specified video output.
    
    Args:
        serial_number (str): The serial number of the target player.
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. Defaults to 0.
    
    Returns:
        dict: Array of available video mode objects, each containing properties like
              modename, width, height, frequency, colorspace, colordepth, etc.
    
    Example:
        >>> modes = get_device_video_modes("ABC123")
        >>> for mode in modes['data']['result']:
        ...     print(f"{mode['modename']}: {mode['width']}x{mode['height']} @ {mode['frequency']}Hz")
    '''
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/modes/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_video_current_mode(serial_number: str, mode_type: str | None = None,
                                  connector: str = "hdmi", device: int = 0) -> dict:
    '''
    Retrieves the current, best, active, or configured video mode on the specified output.
    
    Args:
        serial_number (str): The serial number of the target player.
        mode_type (str, optional): Type of mode to retrieve. 
            Valid values: "best", "active", "configured", None (current mode). 
            Defaults to None.
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. Defaults to 0.
    
    Returns:
        dict: Video mode information for the requested mode type.
    
    Raises:
        ValueError: If mode_type is not valid.
    
    Example:
        >>> # Get current mode
        >>> current = get_device_video_current_mode("ABC123")
        
        >>> # Get best available mode
        >>> best = get_device_video_current_mode("ABC123", mode_type="best")
        
        >>> # Get active mode
        >>> active = get_device_video_current_mode("ABC123", mode_type="active")
    '''
    valid_mode_types = ["best", "active", "configured", None]
    if mode_type not in valid_mode_types:
        raise ValueError(
            f"Invalid mode_type: '{mode_type}'. "
            f"Must be one of: {', '.join([str(m) for m in valid_mode_types])}"
        )
    
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/mode/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    if mode_type == "best":
        params["best"] = "1"
    elif mode_type == "active":
        params["active"] = "1"
    elif mode_type == "configured":
        params["configured"] = "1"
    
    return _get_request(url=url, params=params)


def set_device_video_mode(serial_number: str, mode_name: str, 
                          connector: str = "hdmi", device: int = 0,
                          color_depth: str | None = None, color_space: str | None = None,
                          overscan: bool | None = None) -> dict:
    '''
    Changes the video mode on the player. This will typically cause the player to reboot.
    
    Args:
        serial_number (str): The serial number of the target player.
        mode_name (str): The video mode name (e.g., "1920x1080x60p", "3840x2160x30p").
        connector (str, optional): The video connector type. Currently always "hdmi". Defaults to "hdmi".
        device (int, optional): Output device number. Defaults to 0.
        color_depth (str, optional): Color depth ("8bit", "10bit", "12bit").
        color_space (str, optional): Color space ("rgb", "yuv420", "yuv422").
        overscan (bool, optional): Whether to use overscan setting.
    
    Returns:
        dict: Response indicating success and whether player will reboot.
    
    Example:
        >>> # Set to 1080p60
        >>> result = set_device_video_mode("ABC123", "1920x1080x60p")
        >>> if result['data']['result']['reboot']:
        ...     print("Player is rebooting to apply new video mode")
        
        >>> # Set 4K mode with specific color space
        >>> set_device_video_mode("ABC123", "3840x2160x30p", 
        ...                       color_space="yuv420", color_depth="10bit")
    '''
    url = f"https://ws.bsn.cloud/rest/v1/video/{connector}/output/{device}/mode/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    mode_config: dict[str, str | bool | int] = {
        "modename": mode_name
    }
    
    if color_depth is not None:
        mode_config["colordepth"] = color_depth
    if color_space is not None:
        mode_config["colorspace"] = color_space
    if overscan is not None:
        mode_config["overscan"] = overscan
    
    payload = {
        "data": {
            "name": mode_config
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)

# Advanced Endpoints
def get_device_property_lock(serial_number: str) -> dict:
    '''
    Returns the property lock setting and registry override status for the player.
    
    Property lock controls whether the player's local settings can be modified.
    This endpoint shows if the settings handler is enabled and whether registry 
    settings take priority.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Property lock information including:
            - settingsHandlerEnabled: Whether the settings handler is enabled
            - forceRegistrySettings: Whether registry settings take priority
            - registryEnableSettings: Registry value for enable settings handler
            - bsnce: Whether BSN.cloud is enabled
    
    Example:
        >>> status = get_device_property_lock("ABC123")
        >>> if status['data']['result']['settingshandlerenabled']:
        ...     print("Settings handler is enabled")
        >>> if status['data']['result']['forceregistrysettings']:
        ...     print("Registry settings take priority")
    '''
    url = "https://ws.bsn.cloud/rest/v1/advanced/property-lock/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_device_property_lock(serial_number: str, force_registry_settings: bool, 
                             registry_enable_settings: bool) -> dict:
    '''
    Overrides the current property lock setting on the player.
    This will typically cause the player to reboot.
    
    Args:
        serial_number (str): The serial number of the target player.
        force_registry_settings (bool): Whether registry settings should take priority 
            over other settings.
        registry_enable_settings (bool): Registry value for enabling the settings handler.
    
    Returns:
        dict: Response indicating success and whether player will reboot.
    
    Example:
        >>> # Enable registry settings priority (will cause reboot)
        >>> result = set_device_property_lock("ABC123", 
        ...                                   force_registry_settings=True,
        ...                                   registry_enable_settings=True)
        >>> if result['data']['result']['reboot']:
        ...     print("Player is rebooting to apply property lock changes")
        
        >>> # Disable registry settings priority
        >>> set_device_property_lock("ABC123", 
        ...                          force_registry_settings=False,
        ...                          registry_enable_settings=False)
    '''
    url = "https://ws.bsn.cloud/rest/v1/advanced/property-lock/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "forceRegistrySettings": force_registry_settings,
            "registryEnableSettings": registry_enable_settings
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)

# Registry Endpoints
def get_device_registry(serial_number: str) -> dict:
    '''
    Returns the complete player registry dump with all sections and keys.
    
    The registry contains configuration settings organized into sections like
    'brightscript', 'networking', 'autorun', etc.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Complete registry dump with all sections and their key-value pairs.
    
    Example:
        >>> registry = get_device_registry("ABC123")
        >>> networking = registry['data']['result']['value']['networking']
        >>> print(f"DHCP enabled: {networking.get('dhcp')}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/registry/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_device_registry_key(serial_number: str, section: str, key: str) -> dict:
    '''
    Returns a specific registry key value from the specified section.
    
    Args:
        serial_number (str): The serial number of the target player.
        section (str): The registry section name (e.g., "networking", "brightscript", "html").
        key (str): The registry key name within the section.
    
    Returns:
        dict: Registry key information including section, key, and value.
    
    Example:
        >>> # Get telnet port from networking section
        >>> result = get_device_registry_key("ABC123", "networking", "telnet")
        >>> telnet_port = result['data']['result']['value']
        
        >>> # Get DHCP setting
        >>> dhcp = get_device_registry_key("ABC123", "networking", "dhcp")
        >>> print(f"DHCP: {dhcp['data']['result']['value']}")
    '''
    url = f"https://ws.bsn.cloud/rest/v1/registry/{section}/{key}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_device_registry_key(serial_number: str, section: str, key: str, value: Any) -> dict:
    '''
    Sets a value in the specified section of the registry.
    
    WARNING: Applications rely on registry values. Be careful when modifying registry 
    settings to avoid putting the player in an unstable state. It's recommended to 
    use get_device_registry() or get_device_registry_key() first to see available keys.
    
    Args:
        serial_number (str): The serial number of the target player.
        section (str): The registry section name (e.g., "networking", "brightscript", "html").
        key (str): The registry key name within the section.
        value (Any): The value to set (string, int, bool, etc.).
    
    Returns:
        dict: Response indicating success and the updated key-value pair.
    
    Example:
        >>> # Set telnet port
        >>> set_device_registry_key("ABC123", "networking", "telnet", 23)
        
        >>> # Enable DHCP
        >>> set_device_registry_key("ABC123", "networking", "dhcp", "yes")
        
        >>> # Create a custom key in a new section
        >>> set_device_registry_key("ABC123", "customsection", "customkey", "customvalue")
    '''
    url = f"https://ws.bsn.cloud/rest/v1/registry/{section}/{key}/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "value": value
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def delete_device_registry_key(serial_number: str, section: str, key: str | None = None) -> dict:
    '''
    Deletes a key-value pair from the specified registry section, or the entire section.
    
    WARNING: Applications rely on registry values. Be careful when deleting registry 
    settings to avoid putting the player in an unstable state.
    
    Args:
        serial_number (str): The serial number of the target player.
        section (str): The registry section name (e.g., "networking", "brightscript", "html").
        key (str, optional): The registry key name to delete. If None, deletes the entire section.
    
    Returns:
        dict: Response indicating success and what was deleted.
    
    Example:
        >>> # Delete a specific key
        >>> delete_device_registry_key("ABC123", "networking", "telnet")
        
        >>> # Delete an entire section
        >>> delete_device_registry_key("ABC123", "customsection")
    '''
    if key:
        url = f"https://ws.bsn.cloud/rest/v1/registry/{section}/{key}/"
    else:
        url = f"https://ws.bsn.cloud/rest/v1/registry/{section}/"
    
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _delete_request(url=url, params=params)


def flush_device_registry(serial_number: str) -> dict:
    '''
    Flushes the registry immediately to disk.
    
    This is useful when you've made registry changes and want to ensure they're 
    persisted immediately rather than waiting for the normal flush cycle.
    
    Note: Available as of BOS 9.0.110 and 8.5.47. On earlier OS versions, 
    you need to reboot the player to flush the registry.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Response indicating if flush was successful.
    
    Example:
        >>> # Make registry changes
        >>> set_device_registry_key("ABC123", "networking", "telnet", 23)
        >>> # Flush to disk immediately
        >>> flush_device_registry("ABC123")
    '''
    url = "https://ws.bsn.cloud/rest/v1/registry/flush/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _put_request(url=url, params=params, payload=None)


def get_device_recovery_url(serial_number: str) -> dict:
    '''
    Retrieves the recovery URL stored in the player registry.
    
    The recovery URL is used by the player to download recovery/setup information.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Recovery URL information.
    
    Example:
        >>> result = get_device_recovery_url("ABC123")
        >>> recovery_url = result['data']['result']['value']
        >>> print(f"Recovery URL: {recovery_url}")
    '''
    url = "https://ws.bsn.cloud/rest/v1/registry/recovery-url/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_device_recovery_url(serial_number: str, recovery_url: str) -> dict:
    '''
    Writes a new recovery URL to the player registry.
    
    Args:
        serial_number (str): The serial number of the target player.
        recovery_url (str): The new recovery URL (e.g., "https://handlers.bsn.cloud/recovery/recovery.ashx").
    
    Returns:
        dict: Response indicating if the write was successful.
    
    Example:
        >>> # Set custom recovery URL
        >>> set_device_recovery_url("ABC123", "https://myserver.com/recovery")
        
        >>> # Set to default BSN.cloud recovery URL
        >>> set_device_recovery_url("ABC123", 
        ...                         "https://handlers.bsn.cloud/recovery/recovery.ashx")
    '''
    url = "https://ws.bsn.cloud/rest/v1/registry/recovery-url/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "url": recovery_url
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


# Display Control Endpoints - Built in only
# Note: These APIs can only be used on Moka displays with built-in BrightSign players
# and are only available in BOS 9.0.189 and above.

def get_display_control_all(serial_number: str) -> dict:
    '''
    Returns all control settings for a display connected to a BrightSign player.
    
    Note: Only available for Moka displays with built-in BrightSign players (BOS 9.0.189+).
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: All display control settings including:
            - tvinfo: Display information (MAC address, serial, OS version, etc.)
            - whitebalance: RGB balance settings
            - volume: Volume level
            - brightness: Brightness level
            - contrast: Contrast level
            - idleStandbyTimeout: Standby timeout in seconds
            - powerSetting: Power state ("on", "standby", etc.)
            - videoOutput: Video output selection (e.g., "hdmi1", "hdmi2")
            - sdConnection: SD card control ("brightsign" or "display")
            - alwaysConnectedEnabled: Always connected status
    
    Example:
        >>> settings = get_display_control_all("ABC123")
        >>> volume = settings['data']['result']['volume']
        >>> brightness = settings['data']['result']['brightness']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_display_brightness(serial_number: str) -> dict:
    '''
    Returns the brightness setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Brightness level (0-100).
    
    Example:
        >>> result = get_display_brightness("ABC123")
        >>> brightness = result['data']['result']['brightness']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/brightness/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_brightness(serial_number: str, brightness: int) -> dict:
    '''
    Changes the brightness setting of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        brightness (int): Brightness level (0-100).
    
    Returns:
        dict: Response with updated brightness setting.
    
    Example:
        >>> set_display_brightness("ABC123", 75)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/brightness/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "brightness": brightness
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_contrast(serial_number: str) -> dict:
    '''
    Returns the contrast setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Contrast level (0-100).
    
    Example:
        >>> result = get_display_contrast("ABC123")
        >>> contrast = result['data']['result']['contrast']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/contrast/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_contrast(serial_number: str, contrast: int) -> dict:
    '''
    Changes the contrast of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        contrast (int): Contrast level (0-100).
    
    Returns:
        dict: Response with updated contrast setting.
    
    Example:
        >>> set_display_contrast("ABC123", 60)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/contrast/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "contrast": contrast
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_always_connected(serial_number: str) -> dict:
    '''
    Returns the "always connected" setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Always connected status (enabled: true/false).
    
    Example:
        >>> result = get_display_always_connected("ABC123")
        >>> is_enabled = result['data']['result']['enabled']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/always-connected/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_always_connected(serial_number: str, enable: bool) -> dict:
    '''
    Changes the "always connected" setting of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        enable (bool): True to enable always connected, False to disable.
    
    Returns:
        dict: Response with updated setting.
    
    Example:
        >>> set_display_always_connected("ABC123", True)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/always-connected/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "enable": enable
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_always_on(serial_number: str) -> dict:
    '''
    Returns the "always on" connection setting for a BrightSign connected display.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Always on status (enabled: true/false).
    
    Example:
        >>> result = get_display_always_on("ABC123")
        >>> is_enabled = result['data']['result']['enabled']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/always-on/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_always_on(serial_number: str, enable: bool) -> dict:
    '''
    Sets the display connection to always on.
    
    Args:
        serial_number (str): The serial number of the target player.
        enable (bool): True to enable always on, False to disable.
    
    Returns:
        dict: Response with updated setting.
    
    Example:
        >>> set_display_always_on("ABC123", True)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/always-on/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "enable": enable
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def update_display_firmware(serial_number: str, filepath: str | None = None, url: str | None = None) -> dict:
    '''
    Updates the firmware for a display connected to a BrightSign player.
    This will reboot the player.
    
    Args:
        serial_number (str): The serial number of the target player.
        filepath (str, optional): Path to firmware file relative to SD card.
        url (str, optional): URL to download firmware from.
    
    Returns:
        dict: Response indicating success and reboot status.
    
    Raises:
        ValueError: If neither filepath nor url is provided, or if both are provided.
    
    Example:
        >>> # Update from local file
        >>> update_display_firmware("ABC123", filepath="firmware/tv_firmware.zip")
        
        >>> # Update from URL
        >>> update_display_firmware("ABC123", url="https://example.com/tv_firmware.zip")
    '''
    if (filepath is None and url is None) or (filepath is not None and url is not None):
        raise ValueError("Must provide either filepath or url, but not both")
    
    api_url = "https://ws.bsn.cloud/rest/v1/display-control/firmware/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {"data": {}}
    if filepath:
        payload["data"]["filepath"] = filepath
    else:
        payload["data"]["url"] = url
    
    return _put_request(url=api_url, params=params, payload=payload)


def get_display_info(serial_number: str) -> dict:
    '''
    Returns information about the display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Display information including:
            - macAddress: Display MAC address
            - wifiMacAddress: Display WiFi MAC address
            - serialNo: Display serial number
            - osVersion: Display OS version
            - hwRevision: Hardware revision
    
    Example:
        >>> info = get_display_info("ABC123")
        >>> serial = info['data']['result']['serialno']
        >>> os_version = info['data']['result']['osversion']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/info/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def get_display_power_settings(serial_number: str) -> dict:
    '''
    Returns the power settings for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Power setting (e.g., "on", "standby").
    
    Example:
        >>> result = get_display_power_settings("ABC123")
        >>> power_state = result['data']['result']['setting']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/power-settings/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_power_settings(serial_number: str, setting: str) -> dict:
    '''
    Changes the power setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        setting (str): Power setting (e.g., "on", "standby").
    
    Returns:
        dict: Response with updated power setting.
    
    Example:
        >>> # Turn display on
        >>> set_display_power_settings("ABC123", "on")
        
        >>> # Put display in standby
        >>> set_display_power_settings("ABC123", "standby")
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/power-settings/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "setting": setting
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_standby_timeout(serial_number: str) -> dict:
    '''
    Returns the standby/timeout setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Standby timeout in seconds.
    
    Example:
        >>> result = get_display_standby_timeout("ABC123")
        >>> timeout = result['data']['result']['seconds']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/standby-timeout/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_standby_timeout(serial_number: str, seconds: int) -> dict:
    '''
    Changes the standby/timeout setting of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        seconds (int): Standby timeout in seconds.
    
    Returns:
        dict: Response with updated timeout setting.
    
    Example:
        >>> # Set 5 minute timeout
        >>> set_display_standby_timeout("ABC123", 300)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/standby-timeout/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "seconds": seconds
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_sd_connection(serial_number: str) -> dict:
    '''
    Returns the SD connection setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: SD connection setting ("brightsign" or "display").
    
    Example:
        >>> result = get_display_sd_connection("ABC123")
        >>> connection = result['data']['result']['connection']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/sd-connection/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_sd_connection(serial_number: str, connection: str) -> dict:
    '''
    Changes the SD connection setting of a display connected to a BrightSign player.
    
    The SD card control is passed either to the display or the BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        connection (str): SD connection setting ("brightsign" or "display").
    
    Returns:
        dict: Response with updated SD connection setting.
    
    Raises:
        ValueError: If connection is not "brightsign" or "display".
    
    Example:
        >>> # Give control to BrightSign player
        >>> set_display_sd_connection("ABC123", "brightsign")
        
        >>> # Give control to display
        >>> set_display_sd_connection("ABC123", "display")
    '''
    valid_connections = ["brightsign", "display"]
    if connection not in valid_connections:
        raise ValueError(
            f"Invalid connection: '{connection}'. "
            f"Must be one of: {', '.join(valid_connections)}"
        )
    
    url = "https://ws.bsn.cloud/rest/v1/display-control/sd-connection/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "connection": connection
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_video_output(serial_number: str) -> dict:
    '''
    Returns the video output setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Video output setting (e.g., "hdmi1", "hdmi2").
    
    Example:
        >>> result = get_display_video_output("ABC123")
        >>> output = result['data']['result']['output']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/video-output/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_video_output(serial_number: str, output: str) -> dict:
    '''
    Changes the video output setting of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        output (str): Video output setting (e.g., "hdmi1", "hdmi2").
    
    Returns:
        dict: Response with updated video output setting.
    
    Example:
        >>> set_display_video_output("ABC123", "hdmi2")
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/video-output/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "output": output
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_volume(serial_number: str) -> dict:
    '''
    Returns the volume setting for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: Volume level (0-100).
    
    Example:
        >>> result = get_display_volume("ABC123")
        >>> volume = result['data']['result']['volume']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/volume/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_volume(serial_number: str, volume: int) -> dict:
    '''
    Changes the volume of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        volume (int): Volume level (0-100).
    
    Returns:
        dict: Response with updated volume setting.
    
    Example:
        >>> set_display_volume("ABC123", 75)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/volume/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "volume": volume
        }
    }
    
    return _put_request(url=url, params=params, payload=payload)


def get_display_white_balance(serial_number: str) -> dict:
    '''
    Returns the white balance settings for a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
    
    Returns:
        dict: White balance settings with redBalance, greenBalance, and blueBalance values.
    
    Example:
        >>> result = get_display_white_balance("ABC123")
        >>> red = result['data']['result']['redbalance']
        >>> green = result['data']['result']['greenbalance']
        >>> blue = result['data']['result']['bluebalance']
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/white-balance/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    return _get_request(url=url, params=params)


def set_display_white_balance(serial_number: str, red_balance: int, 
                               green_balance: int, blue_balance: int) -> dict:
    '''
    Changes the white balance of a display connected to a BrightSign player.
    
    Args:
        serial_number (str): The serial number of the target player.
        red_balance (int): Red balance value.
        green_balance (int): Green balance value.
        blue_balance (int): Blue balance value.
    
    Returns:
        dict: Response with updated white balance settings.
    
    Example:
        >>> set_display_white_balance("ABC123", 120, 120, 120)
    '''
    url = "https://ws.bsn.cloud/rest/v1/display-control/white-balance/"
    params = {
        "destinationType": "player",
        "destinationName": serial_number
    }
    
    payload = {
        "data": {
            "redbalance": red_balance,
            "greenbalance": green_balance,
            "bluebalance": blue_balance
        }
    }
    

    return _put_request(url=url, params=params, payload=payload)
