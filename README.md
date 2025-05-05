# ise_api_client
Client tool for interacting with Cisco ISE API with Web GUI

# Cisco ISE API Client

## Overview

This repository is a client tool for interacting with the Cisco Identity Services Engine (ISE) API.  It primarily provides the following functions:

* Retrieving current authentication information
* Displaying a list of Endpoint Groups
* Displaying a list of Endpoints
* Adding MAC addresses to Endpoint Groups
* Deleting MAC addresses from Endpoint Groups

**Disclaimer:**

* This project was created as an experiment in collaboration with Gemini 2.0 flash.  It should be used with caution.

## Features

* Retrieves the current authentication information from the ISE server.
* Displays a list of Endpoint Groups configured on the ISE server.
* Displays a list of Endpoints registered with the ISE server.
* Allows adding a MAC address to a specified Endpoint Group.
* Allows deleting a MAC address from a specified Endpoint Group.

## Environment

* Cisco ISE
* Python 3.x
* Required Python libraries (see requirements.txt)

## インストール

1.  Clone the repository:

    ```bash
    git clone https://github.com/urikura/ise_api_client/
    cd ise_api_client
    pip install -r requirements.txt
    ```
2.  (option) Create a Python virtual environment and install the necessary libraries:

    **Using uv:**

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env
    cd ise_api_client
    uv init
    uv sync
    . .venv/bin/activate
    uv add -r requirements.txt
    ```

3.  Create a `.env` file and enter your ISE IP address, username, and password:

    ```
    ISE_IP=your_ise_ip_address
    ISE_USERNAME=your_ise_username
    ISE_PASSWORD=your_ise_password 
    HTTP_PROXY=http://your_proxy_address:port # optional
    ```

## 使い方

1.  Run the application:

    ```bash
    python3 ise_api_client.py
    ```
2.  Access the web interface in your browser at `http://localhost:5000`.

## Functionality Details

### Current Authentication Information

* Displays the current authentication information for logged-in users on the ISE.
* Provides filtering capabilities by IP address, MAC address, and session ID.

### Endpoint Group List

* Displays a list of Endpoint Groups configured on the ISE.
* Allows filtering the list by group name.

### Endpoint List

* Displays a list of Endpoints registered on the ISE.
* Allows filtering the list by MAC address.

### Add/Delete MAC Address

* Allows adding a specified MAC address to an Endpoint Group.
* Allows deleting a specified MAC address from an Endpoint Group.

## Additional Information

* Modify the settings in `config.py` as needed.
* Check `logs/error.log` for any errors.

## Disclaimer

Use this tool at your own risk. The author is not responsible for any damages caused by the use of this tool.

