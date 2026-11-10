"""Which postings are student roles. Titles are real ones from the feeds, plus the traps."""

import pytest

from radar import kind


@pytest.mark.parametrize(
    "title",
    [
        "Machine Learning - Intern",
        "Intern, Technical Program Management - Dubai, United Arab Emirates",
        "AI Engineer Internship - LLM Data",
        "2027 Program Manager Intern",
        "Data Center Technician - 2027 Internship",
        "Tamara Internship Program",
        "Summer Internship 2026 - Environment, Sustainability & Risk",
        "Electrical & Mechanical Engineering Operations Trainee, AWS Data Centers (UAE National Only)",
        "Working Student - Marketing",
        "Industrial Placement - Finance",
        "Software Engineering Co-op",
        "Global Markets Summer Internship 2027 - Product Management",
    ],
)
def test_internships(title):
    assert kind.classify(title).kind == "internship"


@pytest.mark.parametrize(
    "title",
    [
        "Associate Analyst, Business Administration- Launch Program 2027 - Dubai, UAE",
        "Global Markets Launch Graduate Rotational Program 2027 - Associate Product Specialist",
        "UAE National Graduates",
        "Graduate Engineer",
        "Graduate Programme 2027 - Technology",
        "New Grad Software Engineer",
        "Management Trainee",
        "Early Careers - Analyst",
    ],
)
def test_graduate_programmes(title):
    assert kind.classify(title).kind == "graduate"


@pytest.mark.parametrize(
    "title",
    [
        "Manager, Internal Audit Quality and Excellence (IT Audits) (UAEN)",
        "Assistant Manager - Internal Audit Assurance",
        "Head of Internal Audit",
        "Full-Stack Engineer (Internal Tools)",
        "Vice President - International Sales",
        "Early Careers Recruiter",
        "Campus Recruiter, EMEA",
        "Internship Programme Manager",
        "Graduate Program Lead",
        "University Relations Manager",
        "Senior Software Engineer",
        "Director - Credit Product Lead, CEMEA",
        "Head of Talent Acquisition, CEMEA",
        "Internist Physician",
    ],
)
def test_not_student_roles(title):
    assert kind.classify(title, "You will need 5+ years of experience.").kind is None


def test_reason_names_the_words_that_decided():
    assert kind.classify("Machine Learning - Intern").reason == 'title says "Intern"'


def test_feed_field_can_say_intern_when_the_title_does_not():
    verdict = kind.classify("Data Analyst", "", employment_type="Internship")
    assert verdict.kind == "internship"
    assert "Internship" in verdict.reason


@pytest.mark.parametrize(
    "title, text, expected",
    [
        ("Associate Data Scientist", "You have at least 1 year of relevant experience in analytics.", "first_job"),
        ("Junior Accountant", "0-2 years of experience in accounting.", "first_job"),
        ("Operations Associate", "No prior experience is required for this role.", "first_job"),
        ("Software Engineer", "Fresh graduates are welcome to apply.", "first_job"),
        ("Junior Developer", "We build payment tools for merchants.", "first_job"),
        ("Software Engineer", "3+ years of experience building backend services.", None),
        ("Junior Analyst", "Minimum of three years' experience in consulting.", None),
        ("Account Executive", "We build payment tools for merchants.", None),
    ],
)
def test_first_jobs_need_the_posting_to_say_so(title, text, expected):
    assert kind.classify(title, text).kind == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2+ years of experience", 2),
        ("0 to 2 years of experience in AML", 0),
        ("minimum of three years' experience", 3),
        ("Experience: 1-3 years", 1),
        ("We have been in business for 20 years.", None),
    ],
)
def test_min_years(text, expected):
    got = kind.min_years(text)
    assert (got[0] if got else None) == expected


def test_looks_student_is_a_cheap_title_check():
    assert kind.looks_student("Machine Learning - Intern")
    assert kind.looks_student("Junior Analyst")
    assert not kind.looks_student("Senior Director, Sales")
    assert not kind.looks_student("Early Careers Recruiter")
