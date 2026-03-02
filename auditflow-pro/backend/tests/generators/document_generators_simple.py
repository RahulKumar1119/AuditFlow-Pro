"""
Simplified Hypothesis strategies for generating random valid document data.
"""

from hypothesis import strategies as st
import string


# Simple helper to generate field with confidence
def field(value, confidence):
    return {"value": value, "confidence": confidence}


@st.composite
def w2_data_strategy(draw):
    """Generate random valid W2 form data"""
    return {
        "document_type": "W2",
        "tax_year": field("2023", draw(st.floats(min_value=0.95, max_value=0.99))),
        "employer_name": field(
            draw(st.text(alphabet=string.ascii_letters + " ", min_size=10, max_size=30)),
            draw(st.floats(min_value=0.85, max_value=0.99))
        ),
        "employee_name": field(
            f"{draw(st.sampled_from(['John', 'Jane', 'Michael', 'Sarah']))} {draw(st.sampled_from(['Smith', 'Johnson', 'Williams']))}",
            draw(st.floats(min_value=0.90, max_value=0.99))
        ),
        "wages": field(
            round(draw(st.floats(min_value=20000.0, max_value=200000.0)), 2),
            draw(st.floats(min_value=0.90, max_value=0.99))
        )
    }


@st.composite
def bank_statement_data_strategy(draw):
    """Generate random valid bank statement data"""
    return {
        "document_type": "BANK_STATEMENT",
        "bank_name": field(
            draw(st.sampled_from(["First National Bank", "Community Credit Union"])),
            draw(st.floats(min_value=0.90, max_value=0.99))
        ),
        "account_holder_name": field(
            f"{draw(st.sampled_from(['John', 'Jane', 'Michael']))} {draw(st.sampled_from(['Smith', 'Johnson']))}",
            draw(st.floats(min_value=0.90, max_value=0.98))
        ),
        "ending_balance": field(
            round(draw(st.floats(min_value=100.0, max_value=100000.0)), 2),
            draw(st.floats(min_value=0.90, max_value=0.98))
        )
    }


# Export simplified strategies
any_document_strategy = st.one_of(
    w2_data_strategy(),
    bank_statement_data_strategy()
)
