# Cisco ISE API Client (Flask Web GUI)

A simple Flask web application providing a graphical user interface (GUI) to interact with Cisco Identity Services Engine (ISE) using its ERS and XML APIs.

## Overview

This project implements a basic web client for Cisco ISE, allowing users to perform common tasks such as viewing active sessions and endpoint information, as well as adding and deleting endpoints via a web browser. The application is built with Flask for the backend and a simple HTML/JavaScript frontend using Tailwind CSS for styling. It reads ISE connection details securely from a `.env` file.

**This project was developed experimentally with the assistance of Google's Gemini 2.5 Flash.**

## Features

* Displays Cisco ISE connection details (IP Address, Username) loaded from the `.env` file.
* Fetches and displays a list of active sessions, showing their MAC addresses and the total count (uses ISE XML API).
* Fetches and displays a comprehensive list of configured endpoints, including:
    * MAC Address
    * Assigned Endpoint Group ID
    * Assigned Endpoint Group Name (involves chained ERS API calls)
* Allows deleting an endpoint by its MAC address (searches for the endpoint ID internally by listing all, then calls the ERS DELETE API `/ers/config/endpoint/{endpointId}`).
* Allows adding a new endpoint to a specific Endpoint Group by providing the MAC address and the target Endpoint Group ID (calls the ERS POST API `/ers/config/endpoint` with `ERSEndPoint` payload).
* Basic filtering functionality for sessions and endpoints on the GUI.
* Logging of API requests and responses on the backend.

## Requirements

* Python 3.6 or higher
* Flask
* Requests library (`pip install Flask requests python-dotenv`)
* Access to a Cisco ISE instance with ERS API enabled.
* An ISE user account with appropriate permissions including ERS admin and MNT admin.

## Setup

1.  Clone this repository:
    ```bash
    git clone <repository_url>
    cd ise_api_client
    ```
2.  Create a Python virtual environment (recommended):
    ```bash
    python -m venv .venv
    ```
3.  Activate the virtual environment:
    * On macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
    * On Windows:
        ```bash
        .venv\Scripts\activate
        ```
4.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    (Make sure `requirements.txt` contains `Flask`, `requests`, `python-dotenv`). If not, run `pip freeze > requirements.txt` after manual installation.
5.  Create a `.env` file in the root directory of the project with your Cisco ISE connection details:
    ```env
    ISE_IP=your_ise_ip_address
    ISE_USERNAME=your_ise_api_username
    ISE_PASSWORD=your_ise_api_password
    # Optional: Configure a proxy if needed
    # HTTP_PROXY=http://your_proxy_server:port
    # HTTPS_PROXY=https://your_proxy_server:port # Requests library often uses HTTP_PROXY for both http/https if not specified separately
    ```
    Replace `your_ise_ip_address`, `your_ise_api_username`, and `your_ise_api_password` with your actual ISE details.

## How to Run

1.  Activate your virtual environment (if not already active).
2.  Run the Flask application:
    ```bash
    python ise_api_client.py
    ```
3.  Open your web browser and navigate to `http://127.0.0.1:5001/`.

The application will run on port 5001 by default.

## Usage

Once the application is running and you access the web interface:

* The configured ISE IP and Username from your `.env` file will be displayed at the top.
* Click the "Get Active Sessions" button to fetch and display currently active sessions by their MAC addresses.
* Click the "Get Endpoint List" button to fetch and display all configured endpoints with their MAC address, Group ID, and Group Name. This process involves multiple API calls per endpoint on the backend and may take some time depending on the number of
