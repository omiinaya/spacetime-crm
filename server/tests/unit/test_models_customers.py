import pytest
from pydantic import ValidationError


def test_customer_create():
    from models.customers import CustomerCreate

    c = CustomerCreate(first_name="John", last_name="Doe")
    assert c.first_name == "John"


def test_customer_update():
    from models.customers import CustomerUpdate

    c = CustomerUpdate(first_name="Jane", last_name="Doe")
    assert c.first_name == "Jane"
