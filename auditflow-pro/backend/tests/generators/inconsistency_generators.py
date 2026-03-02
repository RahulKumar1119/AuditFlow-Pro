"""
Hypothesis strategies for generating random inconsistencies in document data.
"""

from hypothesis import strategies as st
import random
import string


@st.composite
def name_variation_strategy(draw, base_name=None):
    """
    Generate name variations with spelling differences.
    
    Creates variations like:
    - "John Doe" -> "Jon Doe" (missing letter)
    - "Sarah Smith" -> "Sara Smith" (spelling variation)
    - "Michael Brown" -> "Micheal Brown" (transposed letters)
    """
    if base_name is None:
        first_names = ["John", "Jane", "Michael", "Sarah", "Robert", "Emily"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        base_name = f"{draw(st.sampled_from(first_names))} {draw(st.sampled_from(last_names))}"
    
    variation_type = draw(st.sampled_from([
        "drop_letter",
        "add_letter",
        "transpose",
        "substitute"
    ]))
    
    varied_name = base_name  # Default to base name
    
    if variation_type == "drop_letter" and len(base_name) > 5:
        # Remove a random letter (not space)
        non_space_indices = [i for i, c in enumerate(base_name) if c != ' ']
        if non_space_indices:
            idx = draw(st.sampled_from(non_space_indices))
            varied_name = base_name[:idx] + base_name[idx+1:]
    elif variation_type == "add_letter":
        # Add a random letter
        idx = draw(st.integers(min_value=0, max_value=len(base_name)))
        letter = draw(st.sampled_from(string.ascii_lowercase))
        varied_name = base_name[:idx] + letter + base_name[idx:]
    elif variation_type == "transpose" and len(base_name) > 3:
        # Transpose two adjacent letters (not spaces)
        for attempt in range(10):  # Try up to 10 times to find valid position
            idx = draw(st.integers(min_value=0, max_value=len(base_name)-2))
            if base_name[idx] != ' ' and base_name[idx+1] != ' ':
                varied_name = base_name[:idx] + base_name[idx+1] + base_name[idx] + base_name[idx+2:]
                break
    else:  # substitute
        # Substitute a letter (not space)
        non_space_indices = [i for i, c in enumerate(base_name) if c.isalpha()]
        if non_space_indices:
            idx = draw(st.sampled_from(non_space_indices))
            letter = draw(st.sampled_from(string.ascii_lowercase))
            varied_name = base_name[:idx] + letter + base_name[idx+1:]
    
    # Ensure we actually created a variation
    if varied_name == base_name:
        # Force a simple substitution
        if len(base_name) > 0:
            varied_name = base_name[0].lower() + base_name[1:] if base_name[0].isupper() else base_name[0].upper() + base_name[1:]
    
    edit_distance = sum(c1 != c2 for c1, c2 in zip(base_name, varied_name)) + abs(len(base_name) - len(varied_name))
    
    return {
        "original": base_name,
        "variation": varied_name,
        "edit_distance": max(1, edit_distance)  # Ensure at least 1
    }


@st.composite
def address_mismatch_strategy(draw, base_address=None):
    """
    Generate address mismatches.
    
    Creates variations like:
    - Different street numbers: "123 Main St" -> "124 Main St"
    - Different street names: "Oak Avenue" -> "Elm Avenue"
    - Different cities: "Springfield" -> "Shelbyville"
    - Different ZIP codes: "62701" -> "62702"
    """
    if base_address is None:
        street_num = draw(st.integers(min_value=100, max_value=9999))
        street_name = draw(st.sampled_from(["Main", "Oak", "Maple", "Cedar", "Elm"]))
        street_type = draw(st.sampled_from(["Street", "Avenue", "Drive", "Lane"]))
        city = draw(st.sampled_from(["Springfield", "Austin", "Seattle", "Boston"]))
        state = draw(st.sampled_from(["IL", "TX", "WA", "MA"]))
        zip_code = draw(st.integers(min_value=10000, max_value=99999))
        base_address = f"{street_num} {street_name} {street_type}, {city}, {state} {zip_code:05d}"
    
    mismatch_type = draw(st.sampled_from([
        "street_number",
        "street_name",
        "city",
        "zip_code"
    ]))
    
    parts = base_address.split(", ")
    street_part = parts[0]
    city_part = parts[1] if len(parts) > 1 else "Springfield"
    state_zip = parts[2] if len(parts) > 2 else "IL 62701"
    
    if mismatch_type == "street_number":
        # Change street number by 1-10
        street_parts = street_part.split(" ", 1)
        if street_parts[0].isdigit():
            new_num = int(street_parts[0]) + draw(st.integers(min_value=1, max_value=10))
            mismatched = f"{new_num} {street_parts[1]}, {city_part}, {state_zip}"
        else:
            mismatched = base_address
    elif mismatch_type == "street_name":
        # Change street name
        new_street = draw(st.sampled_from(["Pine", "Birch", "Willow", "Cherry", "Ash"]))
        street_parts = street_part.split(" ")
        if len(street_parts) >= 2:
            street_parts[1] = new_street
            mismatched = f"{' '.join(street_parts)}, {city_part}, {state_zip}"
        else:
            mismatched = base_address
    elif mismatch_type == "city":
        # Change city
        new_city = draw(st.sampled_from(["Portland", "Denver", "Phoenix", "Miami"]))
        mismatched = f"{street_part}, {new_city}, {state_zip}"
    else:  # zip_code
        # Change ZIP code
        state_zip_parts = state_zip.split(" ")
        if len(state_zip_parts) == 2 and state_zip_parts[1].isdigit():
            new_zip = int(state_zip_parts[1]) + draw(st.integers(min_value=1, max_value=100))
            mismatched = f"{street_part}, {city_part}, {state_zip_parts[0]} {new_zip:05d}"
        else:
            mismatched = base_address
    
    return {
        "original": base_address,
        "mismatch": mismatched,
        "mismatch_type": mismatch_type
    }


@st.composite
def income_discrepancy_strategy(draw, base_income=None):
    """
    Generate income discrepancies.
    
    Creates discrepancies like:
    - 5-10% difference: $75,000 -> $70,000
    - >10% difference: $75,000 -> $65,000
    """
    if base_income is None:
        base_income = draw(st.floats(min_value=30000.0, max_value=150000.0))
    
    discrepancy_level = draw(st.sampled_from(["5-10%", ">10%"]))
    
    if discrepancy_level == "5-10%":
        percentage = draw(st.floats(min_value=0.05, max_value=0.10))
    else:  # >10%
        percentage = draw(st.floats(min_value=0.10, max_value=0.25))
    
    # Randomly increase or decrease
    direction = draw(st.sampled_from([1, -1]))
    discrepant_income = base_income * (1 + direction * percentage)
    
    actual_percentage = abs(discrepant_income - base_income) / base_income * 100
    
    return {
        "original": round(base_income, 2),
        "discrepant": round(discrepant_income, 2),
        "percentage_difference": round(actual_percentage, 2),
        "severity": "HIGH" if actual_percentage > 10 else "MEDIUM"
    }


@st.composite
def ssn_mismatch_strategy(draw, base_ssn=None):
    """
    Generate SSN mismatches.
    
    Creates variations like:
    - "***-**-1234" -> "***-**-1235" (last digit different)
    - "***-**-1234" -> "***-**-1243" (transposed digits)
    """
    if base_ssn is None:
        last4 = draw(st.integers(min_value=0, max_value=9999))
        base_ssn = f"***-**-{last4:04d}"
    
    # Extract last 4 digits
    last4_str = base_ssn.split("-")[-1]
    
    mismatch_type = draw(st.sampled_from([
        "single_digit",
        "transpose"
    ]))
    
    if mismatch_type == "single_digit":
        # Change one digit
        idx = draw(st.integers(min_value=0, max_value=3))
        new_digit = draw(st.integers(min_value=0, max_value=9))
        mismatched_last4 = last4_str[:idx] + str(new_digit) + last4_str[idx+1:]
    else:  # transpose
        # Transpose two adjacent digits
        if len(last4_str) >= 2:
            idx = draw(st.integers(min_value=0, max_value=2))
            mismatched_last4 = last4_str[:idx] + last4_str[idx+1] + last4_str[idx] + last4_str[idx+2:]
        else:
            mismatched_last4 = last4_str
    
    mismatched_ssn = f"***-**-{mismatched_last4}"
    
    return {
        "original": base_ssn,
        "mismatch": mismatched_ssn,
        "mismatch_type": mismatch_type
    }


@st.composite
def dob_mismatch_strategy(draw, base_dob=None):
    """
    Generate date of birth mismatches.
    
    Creates variations like:
    - "1985-06-15" -> "1985-06-16" (day off by 1)
    - "1985-06-15" -> "1985-07-15" (month different)
    - "1985-06-15" -> "1986-06-15" (year different)
    """
    if base_dob is None:
        from datetime import datetime
        year = draw(st.integers(min_value=1950, max_value=2005))
        month = draw(st.integers(min_value=1, max_value=12))
        day = draw(st.integers(min_value=1, max_value=28))  # Safe day range
        base_dob = f"{year:04d}-{month:02d}-{day:02d}"
    
    mismatch_type = draw(st.sampled_from([
        "day",
        "month",
        "year"
    ]))
    
    parts = base_dob.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    
    if mismatch_type == "day":
        # Change day by 1-3
        new_day = day + draw(st.integers(min_value=1, max_value=3))
        if new_day > 28:
            new_day = day - draw(st.integers(min_value=1, max_value=3))
        mismatched_dob = f"{year:04d}-{month:02d}-{max(1, new_day):02d}"
    elif mismatch_type == "month":
        # Change month
        new_month = draw(st.integers(min_value=1, max_value=12))
        while new_month == month:
            new_month = draw(st.integers(min_value=1, max_value=12))
        mismatched_dob = f"{year:04d}-{new_month:02d}-{day:02d}"
    else:  # year
        # Change year by 1
        new_year = year + draw(st.sampled_from([1, -1]))
        mismatched_dob = f"{new_year:04d}-{month:02d}-{day:02d}"
    
    return {
        "original": base_dob,
        "mismatch": mismatched_dob,
        "mismatch_type": mismatch_type
    }


# Combined strategy for any inconsistency type
any_inconsistency_strategy = st.one_of(
    name_variation_strategy(),
    address_mismatch_strategy(),
    income_discrepancy_strategy(),
    ssn_mismatch_strategy(),
    dob_mismatch_strategy()
)
