# -*- coding: utf-8 -*-
"""
Hypothesis strategies for generating random valid document data.
"""

from hypothesis import strategies as st
from datetime import datetime, timedelta
import string


# Helper strategies
def ssn_strategy():
    """Generate masked SSN in format ***-**-XXXX"""
    return st.builds(
        lambda last4: f"***-**-{last4:04d}",
        st.integers(min_value=0, max_value=9999)
    )


def ein_strategy():
    """Generate EIN in format XX-XXXXXXX"""
    return st.builds(
        lambda part1, part2: f"{part1:02d}-{part2:07d}",
        st.integers(min_value=10, max_value=99),
        st.integers(min_value=1000000, max_value=9999999)
    )


def account_number_strategy():
    """Generate masked account number ****XXXX"""
    return st.builds(
        lambda last4: f"****{last4:04d}",
        st.integers(min_value=0, max_value=9999)
    )


def name_strategy():
    """Generate realistic full names"""
    first_names = ["John", "Jane", "Michael", "Sarah", "Robert", "Emily", "David", "Jennifer", "William", "Lisa"]
    middle_names = ["James", "Marie", "Lee", "Ann", "Michael", "Elizabeth", "Joseph", "Lynn", "Thomas", "Grace"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    return st.builds(
        lambda f, m, l: f"{f} {m} {l}",
        st.sampled_from(first_names),
        st.sampled_from(middle_names),
        st.sampled_from(last_names)
    )


def address_strategy():
    """Generate realistic US addresses"""
    street_numbers = st.integers(min_value=100, max_value=9999)
    street_names = st.sampled_from(["Main", "Oak", "Maple", "Cedar", "Elm", "Pine", "Washington", "Park", "Lake", "Hill"])
    street_types = st.sampled_from(["Street", "Avenue", "Drive", "Lane", "Road", "Boulevard", "Way", "Court"])
    cities = st.sampled_from(["Springfield", "Austin", "Seattle", "Boston", "Denver", "Portland", "Miami", "Phoenix", "Chicago", "Atlanta"])
    states = st.sampled_from(["IL", "TX", "WA", "MA", "CO", "OR", "FL", "AZ", "CA", "NY"])
    zip_codes = st.integers(min_value=10000, max_value=99999)
    
    return st.builds(
        lambda num, name, type, city, state, zip: f"{num} {name} {type}, {city}, {state} {zip:05d}",
        street_numbers, street_names, street_types, cities, states, zip_codes
    )


def date_strategy(min_year=1950, max_year=2010):
    """Generate dates within a range"""
    return st.dates(
        min_value=datetime(min_year, 1, 1).date(),
        max_value=datetime(max_year, 12, 31).date()
    ).map(lambda d: d.strftime("%Y-%m-%d"))


def confidence_strategy(min_conf=0.70, max_conf=0.99):
    """Generate confidence scores"""
    return st.floats(min_value=min_conf, max_value=max_conf)


@st.composite
def field_with_confidence(draw, value_strategy, min_conf=0.70, max_conf=0.99):
    """Wrap a value strategy with confidence score"""
    value = draw(value_strategy)
    conf = draw(confidence_strategy(min_conf, max_conf))
    return {"value": value, "confidence": round(conf, 2)}


# Document-specific strategies

@st.composite
def w2_data_strategy(draw):
    """Generate random valid W2 form data"""
    return {
        "document_type": "W2",
        "tax_year": draw(field_with_confidence(st.just("2023"), 0.95, 0.99)),
        "employer_name": draw(field_with_confidence(
            st.text(alphabet=string.ascii_letters + " ", min_size=5, max_size=50),
            0.85, 0.99
        )),
        "employer_ein": draw(field_with_confidence(ein_strategy(), 0.90, 0.99)),
        "employee_name": draw(field_with_confidence(name_strategy(), 0.90, 0.99)),
        "employee_ssn": draw(field_with_confidence(ssn_strategy(), 0.95, 0.99)),
        "employee_address": draw(field_with_confidence(address_strategy(), 0.80, 0.96)),
        "wages": draw(field_with_confidence(
            st.floats(min_value=20000.0, max_value=200000.0).map(lambda x: round(x, 2)),
            0.90, 0.99
        )),
        "federal_tax_withheld": draw(field_with_confidence(
            st.floats(min_value=2000.0, max_value=50000.0).map(lambda x: round(x, 2)),
            0.90, 0.99
        )),
        "social_security_wages": draw(field_with_confidence(
            st.floats(min_value=20000.0, max_value=200000.0).map(lambda x: round(x, 2)),
            0.90, 0.99
        )),
        "medicare_wages": draw(field_with_confidence(
            st.floats(min_value=20000.0, max_value=200000.0).map(lambda x: round(x, 2)),
            0.90, 0.99
        )),
        "state": draw(field_with_confidence(
            st.sampled_from(["IL", "TX", "WA", "MA", "CO", "OR", "FL", "AZ", "CA", "NY"]),
            0.95, 0.99
        )),
        "state_tax_withheld": draw(field_with_confidence(
            st.floats(min_value=0.0, max_value=15000.0).map(lambda x: round(x, 2)),
            0.90, 0.99
        ))
    }


@st.composite
def bank_statement_data_strategy(draw):
    """Generate random valid bank statement data"""
    return {
        "document_type": "BANK_STATEMENT",
        "bank_name": field_with_confidence(
            st.sampled_from(["First National Bank", "Community Credit Union", "Pacific Trust Bank", "Mega Bank Corp"]),
            0.90, 0.99
        )(draw),
        "account_holder_name": field_with_confidence(name_strategy(), 0.90, 0.98)(draw),
        "account_number": field_with_confidence(account_number_strategy(), 0.95, 0.99)(draw),
        "statement_period_start": field_with_confidence(
            date_strategy(2020, 2023),
            0.95, 0.99
        )(draw),
        "statement_period_end": field_with_confidence(
            date_strategy(2020, 2023),
            0.95, 0.99
        )(draw),
        "beginning_balance": field_with_confidence(
            st.floats(min_value=100.0, max_value=100000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw),
        "ending_balance": field_with_confidence(
            st.floats(min_value=100.0, max_value=100000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw),
        "total_deposits": field_with_confidence(
            st.floats(min_value=1000.0, max_value=50000.0).map(lambda x: round(x, 2)),
            0.85, 0.97
        )(draw),
        "total_withdrawals": field_with_confidence(
            st.floats(min_value=1000.0, max_value=50000.0).map(lambda x: round(x, 2)),
            0.85, 0.97
        )(draw),
        "account_holder_address": field_with_confidence(address_strategy(), 0.80, 0.95)(draw)
    }


@st.composite
def tax_form_data_strategy(draw):
    """Generate random valid 1040 tax form data"""
    return {
        "document_type": "TAX_FORM",
        "form_type": field_with_confidence(st.just("1040"), 0.95, 0.99)(draw),
        "tax_year": field_with_confidence(st.just("2023"), 0.95, 0.99)(draw),
        "taxpayer_name": field_with_confidence(name_strategy(), 0.90, 0.99)(draw),
        "taxpayer_ssn": field_with_confidence(ssn_strategy(), 0.95, 0.99)(draw),
        "spouse_name": field_with_confidence(
            st.one_of(st.none(), name_strategy()),
            0.90, 0.99
        )(draw),
        "filing_status": field_with_confidence(
            st.sampled_from(["Single", "Married Filing Jointly", "Married Filing Separately", "Head of Household"]),
            0.90, 0.99
        )(draw),
        "address": field_with_confidence(address_strategy(), 0.80, 0.96)(draw),
        "wages_salaries": field_with_confidence(
            st.floats(min_value=20000.0, max_value=200000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw),
        "adjusted_gross_income": field_with_confidence(
            st.floats(min_value=20000.0, max_value=200000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw),
        "taxable_income": field_with_confidence(
            st.floats(min_value=10000.0, max_value=180000.0).map(lambda x: round(x, 2)),
            0.85, 0.97
        )(draw),
        "total_tax": field_with_confidence(
            st.floats(min_value=2000.0, max_value=50000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw),
        "federal_tax_withheld": field_with_confidence(
            st.floats(min_value=2000.0, max_value=50000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw),
        "refund_amount": field_with_confidence(
            st.floats(min_value=0.0, max_value=10000.0).map(lambda x: round(x, 2)),
            0.90, 0.98
        )(draw)
    }


@st.composite
def drivers_license_data_strategy(draw):
    """Generate random valid driver's license data"""
    return {
        "document_type": "DRIVERS_LICENSE",
        "state": field_with_confidence(
            st.sampled_from(["IL", "TX", "WA", "MA", "CO", "OR", "FL", "AZ", "CA", "NY"]),
            0.95, 0.99
        )(draw),
        "license_number": field_with_confidence(
            st.text(alphabet=string.ascii_uppercase + string.digits, min_size=8, max_size=15),
            0.90, 0.99
        )(draw),
        "full_name": field_with_confidence(name_strategy(), 0.90, 0.99)(draw),
        "date_of_birth": field_with_confidence(date_strategy(1950, 2005), 0.95, 0.99)(draw),
        "address": field_with_confidence(address_strategy(), 0.80, 0.96)(draw),
        "issue_date": field_with_confidence(date_strategy(2015, 2023), 0.90, 0.98)(draw),
        "expiration_date": field_with_confidence(date_strategy(2024, 2030), 0.90, 0.98)(draw),
        "sex": field_with_confidence(st.sampled_from(["M", "F"]), 0.95, 0.99)(draw),
        "height": field_with_confidence(
            st.sampled_from(["5'2\"", "5'4\"", "5'6\"", "5'8\"", "5'10\"", "6'0\"", "6'2\"", "6'4\""]),
            0.85, 0.96
        )(draw),
        "eye_color": field_with_confidence(
            st.sampled_from(["BRN", "BLU", "GRN", "HAZ", "GRY"]),
            0.90, 0.97
        )(draw)
    }


@st.composite
def id_document_data_strategy(draw):
    """Generate random valid ID document data"""
    return {
        "document_type": "ID_DOCUMENT",
        "id_type": field_with_confidence(
            st.sampled_from(["PASSPORT", "STATE_ID", "OTHER"]),
            0.90, 0.99
        )(draw),
        "document_number": field_with_confidence(
            st.text(alphabet=string.digits, min_size=8, max_size=12),
            0.90, 0.99
        )(draw),
        "full_name": field_with_confidence(name_strategy(), 0.90, 0.99)(draw),
        "date_of_birth": field_with_confidence(date_strategy(1950, 2005), 0.95, 0.99)(draw),
        "issuing_authority": field_with_confidence(
            st.sampled_from([
                "U.S. Department of State",
                "Texas Department of Public Safety",
                "Illinois Secretary of State",
                "U.S. Department of Defense"
            ]),
            0.85, 0.98
        )(draw),
        "issue_date": field_with_confidence(date_strategy(2015, 2023), 0.90, 0.98)(draw),
        "expiration_date": field_with_confidence(date_strategy(2024, 2035), 0.90, 0.98)(draw),
        "nationality": field_with_confidence(st.just("USA"), 0.95, 0.99)(draw)
    }


# Combined strategy for any document type
any_document_strategy = st.one_of(
    w2_data_strategy(),
    bank_statement_data_strategy(),
    tax_form_data_strategy(),
    drivers_license_data_strategy(),
    id_document_data_strategy()
)
