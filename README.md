# EIMS v2 Connector

## Overview
**EIMS v2 Connector** is a custom Odoo module designed to integrate Odoo's accounting/invoicing system with the **Electronic Invoice Management System (EIMS) version 2**. 

This module ensures compliance with local fiscal regulations by automatically registering invoices, credit notes, and withholding receipts with the central tax authority's system. It provides a robust layer of logging, error handling, and reporting to manage fiscal documents effectively directly from Odoo.

## Key Features

### 1. Fiscal Document Registration
- **Customer Invoices**: Automatically registers confirmed invoices with EIMS.
- **Credit Notes**: Handles credit memos/refunds and reports them to EIMS.
- **Withholding Receipts**: Manages and prints withholding tax receipts compliant with EIMS requirements.

### 2. EIMS Integration & Compliance
- **Authentication**: Handles secure authentication with the EIMS API.
- **Cryptographic Security**: Includes utilities for handling cryptographic requirements (`crypto_utils.py`).
- **Real-time Status**: Tracks the status of registered invoices (e.g., Registered, Cancelled).

### 3. Operational Tools
- **Bulk Cancellation**: Wizard to cancel multiple invoices in bulk (`EIMS Bulk Cancel`).
- **Unregistered Invoice Management**: Track and manage invoices that failed to register.
- **Detailed Logging**:
  - **Notification Logs**: Tracks callbacks and notifications from EIMS.
  - **Cancel Logs**: Records cancellation requests and statuses.
  - **Receipt & Credit Logs**: Detailed logs for receipts and credit memos.

### 4. Reporting
- **Custom PDF Reports**:
  - EIMS Invoice Report
  - EIMS Receipt Report
  - EIMS Withholding Receipt Report
- **Email Templates**: Pre-configured email templates for communicating with partners.

## Installation

1. Ensure the module is placed in your Odoo `custom_addons` directory.
2. Install the required dependencies:
   - `account`
   - `contacts`
   - `mail`
3. Update your Odoo app list and install **EIMS v2** (`eims_test_connector_12`).

## Configuration

1. **Company Settings**:
   - Go to your Company settings to configure EIMS credentials (API Keys, Endpoints, TIN, etc.).
   
2. **Partner Settings**:
   - ensure partners (customers/vendors) have valid Tax IDs (TIN) and address details as required by EIMS.

## Usage

- **Invoicing**: Create and confirm a Customer Invoice standard Odoo workflow. The module will attempt to register the invoice with EIMS upon confirmation.
- **Withholding**: Generate withholding receipts from payments or invoices where applicable.
- **Monitoring**: Use the **EIMS Logs** menu (if available) or check the chatter on invoices to see registration status and API responses.

## Technical Details

- **Controllers**: Includes endpoints for callbacks (`bulk_callback.py`, `eims_notification_callback.py`) to receive asynchronous updates from EIMS.
- **Services**: dedicated service layer for HTTP requests (`eims_request.py`) and cryptography (`crypto_utils.py`).

## License
LGPL-3
