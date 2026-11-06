"""Gemini function-calling tool declarations."""

from google.genai import types

# ---------------------------------------------------------------------------
# Household tools
# ---------------------------------------------------------------------------

_LIST_HOUSEHOLDS = types.FunctionDeclaration(
    name="list_households",
    description=(
        "List all households the user has access to. "
        "Call this first if you need to know which households are available."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={},
    ),
)

_CREATE_HOUSEHOLD = types.FunctionDeclaration(
    name="create_household",
    description=(
        "Create a new household for the user. "
        "The user automatically becomes a member. "
        "This works even when the conversation is scoped to an active household."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "name": types.Schema(
                type=types.Type.STRING,
                description="Name of the new household (e.g. 'Vacation Home').",
            ),
            "currency": types.Schema(
                type=types.Type.STRING,
                description=(
                    "3-letter ISO 4217 currency code for the household "
                    "(e.g. USD, EUR, RUB). Defaults to USD."
                ),
            ),
        },
        required=["name"],
    ),
)

_RENAME_HOUSEHOLD = types.FunctionDeclaration(
    name="rename_household",
    description="Rename an existing household.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to rename.",
            ),
            "name": types.Schema(
                type=types.Type.STRING,
                description="New name for the household.",
            ),
        },
        required=["household_id", "name"],
    ),
)

_GENERATE_HOUSEHOLD_INVITE = types.FunctionDeclaration(
    name="generate_household_invite",
    description=(
        "Generate (or regenerate) an invite token for a household so another "
        "person can join it. Returns the invite token."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to generate an invite for.",
            ),
        },
        required=["household_id"],
    ),
)

_JOIN_HOUSEHOLD = types.FunctionDeclaration(
    name="join_household",
    description=(
        "Join a household using an invite token. "
        "This works even when the conversation is scoped to an active household."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "token": types.Schema(
                type=types.Type.STRING,
                description="The household invite token.",
            ),
        },
        required=["token"],
    ),
)

_LEAVE_HOUSEHOLD = types.FunctionDeclaration(
    name="leave_household",
    description=(
        "Remove the user from a household without deleting it for other members. "
        "Only call this after the user explicitly confirms."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to leave.",
            ),
            "confirm": types.Schema(
                type=types.Type.BOOLEAN,
                description=(
                    "Must be true. Set only after the user explicitly confirms "
                    "they want to leave the household."
                ),
            ),
        },
        required=["household_id", "confirm"],
    ),
)

_DELETE_HOUSEHOLD = types.FunctionDeclaration(
    name="delete_household",
    description=(
        "Permanently delete a household and all of its financial records. "
        "Only allowed when the user is the only member and has another household. "
        "Only call this after the user explicitly confirms."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to delete.",
            ),
            "confirm": types.Schema(
                type=types.Type.BOOLEAN,
                description=(
                    "Must be true. Set only after the user explicitly confirms "
                    "they want to permanently delete the household."
                ),
            ),
        },
        required=["household_id", "confirm"],
    ),
)

# ---------------------------------------------------------------------------
# Expense tools
# ---------------------------------------------------------------------------

_ADD_EXPENSE = types.FunctionDeclaration(
    name="add_expense",
    description="Add a new expense record to a household budget.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to add the expense to.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="Name/description of the expense.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="Amount spent (positive number).",
            ),
        },
        required=["household_id", "month", "year", "title", "amount"],
    ),
)

_REMOVE_EXPENSE = types.FunctionDeclaration(
    name="remove_expense",
    description="Remove an expense record by its ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "expense_id": types.Schema(
                type=types.Type.INTEGER,
                description="The expense ID to remove.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
        },
        required=["household_id", "expense_id", "month", "year"],
    ),
)

_UPDATE_EXPENSE = types.FunctionDeclaration(
    name="update_expense",
    description=(
        "Update an existing expense record. "
        "First search for the record to get its ID, then call this tool."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "expense_id": types.Schema(
                type=types.Type.INTEGER,
                description="The expense ID to update.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="New name/description of the expense.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="New amount for the expense.",
            ),
        },
        required=["household_id", "expense_id", "month", "year", "title", "amount"],
    ),
)

# ---------------------------------------------------------------------------
# Income tools
# ---------------------------------------------------------------------------

_ADD_INCOME = types.FunctionDeclaration(
    name="add_income",
    description="Add a new income record to a household budget.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to add income to.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="Source/description of the income.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="Amount received (positive number).",
            ),
        },
        required=["household_id", "month", "year", "title", "amount"],
    ),
)

_REMOVE_INCOME = types.FunctionDeclaration(
    name="remove_income",
    description="Remove an income record by its ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "income_id": types.Schema(
                type=types.Type.INTEGER,
                description="The income ID to remove.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
        },
        required=["household_id", "income_id", "month", "year"],
    ),
)

_UPDATE_INCOME = types.FunctionDeclaration(
    name="update_income",
    description=(
        "Update an existing income record. "
        "First search for the record to get its ID, then call this tool."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "income_id": types.Schema(
                type=types.Type.INTEGER,
                description="The income ID to update.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="New source/description of the income.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="New amount for the income.",
            ),
        },
        required=["household_id", "income_id", "month", "year", "title", "amount"],
    ),
)

# ---------------------------------------------------------------------------
# Asset tools
# ---------------------------------------------------------------------------

_ADD_ASSET = types.FunctionDeclaration(
    name="add_asset",
    description="Add a new asset record (investment, property, etc.).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to add the asset to.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="Name of the asset.",
            ),
            "price": types.Schema(
                type=types.Type.NUMBER,
                description="Price per unit.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="Optional quantity/units held. Defaults to 1.",
            ),
        },
        required=["household_id", "month", "year", "title", "price"],
    ),
)

_REMOVE_ASSET = types.FunctionDeclaration(
    name="remove_asset",
    description="Remove an asset record by its ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "asset_id": types.Schema(
                type=types.Type.INTEGER,
                description="The asset ID to remove.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
        },
        required=["household_id", "asset_id", "month", "year"],
    ),
)

_UPDATE_ASSET = types.FunctionDeclaration(
    name="update_asset",
    description=(
        "Update an existing asset record. "
        "First search for the record to get its ID, then call this tool."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "asset_id": types.Schema(
                type=types.Type.INTEGER,
                description="The asset ID to update.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="New name of the asset.",
            ),
            "price": types.Schema(
                type=types.Type.NUMBER,
                description="New price per unit.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="New optional quantity/units held. Defaults to 1.",
            ),
        },
        required=["household_id", "asset_id", "month", "year", "title"],
    ),
)

# ---------------------------------------------------------------------------
# Liability tools
# ---------------------------------------------------------------------------

_ADD_LIABILITY = types.FunctionDeclaration(
    name="add_liability",
    description="Add a new liability/debt record.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to add the liability to.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="Name/description of the liability.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="Amount owed (positive number).",
            ),
        },
        required=["household_id", "month", "year", "title", "amount"],
    ),
)

_REMOVE_LIABILITY = types.FunctionDeclaration(
    name="remove_liability",
    description="Remove a liability record by its ID.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "liability_id": types.Schema(
                type=types.Type.INTEGER,
                description="The liability ID to remove.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
        },
        required=["household_id", "liability_id", "month", "year"],
    ),
)

_UPDATE_LIABILITY = types.FunctionDeclaration(
    name="update_liability",
    description=(
        "Update an existing liability record. "
        "First search for the record to get its ID, then call this tool."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "liability_id": types.Schema(
                type=types.Type.INTEGER,
                description="The liability ID to update.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month (1-12).",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year (e.g. 2025).",
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="New name/description of the liability.",
            ),
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="New amount owed.",
            ),
        },
        required=[
            "household_id",
            "liability_id",
            "month",
            "year",
            "title",
            "amount",
        ],
    ),
)

# ---------------------------------------------------------------------------
# Bulk / month tools
# ---------------------------------------------------------------------------

_MOVE_RECORD = types.FunctionDeclaration(
    name="move_record",
    description=(
        "Move an expense, income, or liability record to a different month/year. "
        "Use search_records first to get the record ID. Assets cannot be moved "
        "because they are carried forward automatically."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID the record belongs to.",
            ),
            "record_type": types.Schema(
                type=types.Type.STRING,
                description="Type of record: 'expense', 'income', or 'liability'.",
            ),
            "record_id": types.Schema(
                type=types.Type.INTEGER,
                description="The ID of the record to move.",
            ),
            "to_year": types.Schema(
                type=types.Type.INTEGER,
                description="Destination year (e.g. 2026).",
            ),
            "to_month": types.Schema(
                type=types.Type.INTEGER,
                description="Destination month (1-12).",
            ),
        },
        required=[
            "household_id",
            "record_type",
            "record_id",
            "to_year",
            "to_month",
        ],
    ),
)

_COPY_MONTH = types.FunctionDeclaration(
    name="copy_month",
    description=(
        "Copy expenses, income, and/or liabilities from one month to another. "
        "Records with the same title already present in the target month are skipped. "
        "Assets are never copied because they carry forward automatically."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID.",
            ),
            "from_year": types.Schema(
                type=types.Type.INTEGER,
                description="Source year.",
            ),
            "from_month": types.Schema(
                type=types.Type.INTEGER,
                description="Source month (1-12).",
            ),
            "to_year": types.Schema(
                type=types.Type.INTEGER,
                description="Destination year.",
            ),
            "to_month": types.Schema(
                type=types.Type.INTEGER,
                description="Destination month (1-12).",
            ),
            "record_types": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Comma-separated record types to copy: 'expense', 'income', "
                    "'liability', or 'all' (default). Assets are always excluded."
                ),
            ),
        },
        required=[
            "household_id",
            "from_year",
            "from_month",
            "to_year",
            "to_month",
        ],
    ),
)

_ADD_RECORDS_BULK = types.FunctionDeclaration(
    name="add_records_bulk",
    description=(
        "Add several financial records at once for the same household and month. "
        "Use this when the user pastes a list of expenses, income, assets, or "
        "liabilities instead of adding them one by one."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to add the records to.",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year for all records (e.g. 2026).",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month for all records (1-12).",
            ),
            "records": types.Schema(
                type=types.Type.ARRAY,
                description="The records to add.",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "record_type": types.Schema(
                            type=types.Type.STRING,
                            description=(
                                "Type of record: 'expense', 'income', 'asset', "
                                "or 'liability'."
                            ),
                        ),
                        "title": types.Schema(
                            type=types.Type.STRING,
                            description="Name/description of the record.",
                        ),
                        "amount": types.Schema(
                            type=types.Type.NUMBER,
                            description=(
                                "Amount for expense, income, or liability records."
                            ),
                        ),
                        "price": types.Schema(
                            type=types.Type.NUMBER,
                            description="Price per unit (asset records only).",
                        ),
                        "quantity": types.Schema(
                            type=types.Type.NUMBER,
                            description="Units held (asset records only, optional).",
                        ),
                    },
                    required=["record_type", "title"],
                ),
            ),
        },
        required=["household_id", "year", "month", "records"],
    ),
)

# ---------------------------------------------------------------------------
# Query / analytics tools
# ---------------------------------------------------------------------------

_GET_OVERVIEW = types.FunctionDeclaration(
    name="get_overview",
    description=(
        "Get a financial overview/summary for a specific household and time period."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description="The household ID to get overview for.",
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Year to query.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Month to query (optional, omit for yearly overview).",
            ),
        },
        required=["household_id", "year"],
    ),
)

_SEARCH_RECORDS = types.FunctionDeclaration(
    name="search_records",
    description=(
        "Search for financial records (expenses, income, assets, liabilities) "
        "by title and/or amount across all or a specific household. "
        "Supports filtering by exact amount (set both min and max to the same value), "
        "amount range, text query, or any combination."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Search term to match against record titles "
                    "(case-insensitive partial match). "
                    "Can be omitted if searching by amount only."
                ),
            ),
            "record_type": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Type of record to search: "
                    "'expense', 'income', 'asset', 'liability', or 'all'."
                ),
            ),
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description=(
                    "Limit search to a specific household. "
                    "Omit to search all accessible households."
                ),
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Limit search to a specific year.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Limit search to a specific month.",
            ),
            "amount_min": types.Schema(
                type=types.Type.NUMBER,
                description=(
                    "Minimum amount (inclusive). "
                    "For exact match, set both amount_min and amount_max to the same value."
                ),
            ),
            "amount_max": types.Schema(
                type=types.Type.NUMBER,
                description=(
                    "Maximum amount (inclusive). "
                    "For exact match, set both amount_min and amount_max to the same value."
                ),
            ),
        },
        required=["record_type"],
    ),
)

_FIND_DUPLICATES = types.FunctionDeclaration(
    name="find_duplicates",
    description=(
        "Find likely duplicate records: same type, title, amount, and month "
        "within the same household. Use this when the user asks whether they have "
        "duplicates or before adding records that may already exist."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "household_id": types.Schema(
                type=types.Type.INTEGER,
                description=(
                    "Limit the search to a specific household. "
                    "Omit to search all accessible households."
                ),
            ),
            "record_type": types.Schema(
                type=types.Type.STRING,
                description=(
                    "Type of record to check: 'expense', 'income', 'asset', "
                    "'liability', or 'all'."
                ),
            ),
            "year": types.Schema(
                type=types.Type.INTEGER,
                description="Limit the search to a specific year.",
            ),
            "month": types.Schema(
                type=types.Type.INTEGER,
                description="Limit the search to a specific month.",
            ),
        },
        required=["record_type"],
    ),
)

# ---------------------------------------------------------------------------
# Currency tools
# ---------------------------------------------------------------------------

_CONVERT_CURRENCY = types.FunctionDeclaration(
    name="convert_currency",
    description=(
        "Convert an amount from one currency to another using live exchange rates. "
        "Use this when the user asks to convert currencies, compare prices in different "
        "currencies, or when you need to record an amount in the household's currency "
        "but the user specified a different one."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "amount": types.Schema(
                type=types.Type.NUMBER,
                description="The amount to convert (positive number).",
            ),
            "from_currency": types.Schema(
                type=types.Type.STRING,
                description="Source currency code (e.g. USD, EUR, RUB, GBP).",
            ),
            "to_currency": types.Schema(
                type=types.Type.STRING,
                description="Target currency code (e.g. USD, EUR, RUB, GBP).",
            ),
        },
        required=["amount", "from_currency", "to_currency"],
    ),
)

# ---------------------------------------------------------------------------
# Public: complete list of all tool declarations
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS: list[types.FunctionDeclaration] = [
    # Households
    _LIST_HOUSEHOLDS,
    _CREATE_HOUSEHOLD,
    _RENAME_HOUSEHOLD,
    _GENERATE_HOUSEHOLD_INVITE,
    _JOIN_HOUSEHOLD,
    _LEAVE_HOUSEHOLD,
    _DELETE_HOUSEHOLD,
    # Expenses
    _ADD_EXPENSE,
    _REMOVE_EXPENSE,
    _UPDATE_EXPENSE,
    # Income
    _ADD_INCOME,
    _REMOVE_INCOME,
    _UPDATE_INCOME,
    # Assets
    _ADD_ASSET,
    _REMOVE_ASSET,
    _UPDATE_ASSET,
    # Liabilities
    _ADD_LIABILITY,
    _REMOVE_LIABILITY,
    _UPDATE_LIABILITY,
    # Bulk / month
    _MOVE_RECORD,
    _COPY_MONTH,
    _ADD_RECORDS_BULK,
    # Queries
    _GET_OVERVIEW,
    _SEARCH_RECORDS,
    _FIND_DUPLICATES,
    # Currency
    _CONVERT_CURRENCY,
]
