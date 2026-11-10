"""Fact reading. Every case is a sentence taken from a real posting, or a near miss that must not be read."""

import pytest

from radar import facts
from radar.text import sentences


def label(fact):
    return fact.label if fact else None


# ------------------------------------------------------------------ start


@pytest.mark.parametrize(
    "sentence, expected",
    [
        ("Available to start on 1st March or 1st September 2027", "March or September 2027"),
        ("Available to commence an internship between January and December 2027.", "January to December 2027"),
        ("The internship starts mid-June 2027 and has a duration of 12 weeks.", "June 2027"),
        ("Available to work full-time for 10-12 weeks starting June 2027", "June 2027"),
        ("Cohorts: January & June (Yearly) | Function: Multiple, apply once", "January and June"),
        ("Amazon internships are full-time (40 hours per week) for 3 consecutive months, starting in summer 2027.", "Summer 2027"),
        ("Start date: Jan 2027", "January 2027"),
        ("We need someone who can start immediately.", "Immediate start"),
    ],
)
def test_start_is_read(sentence, expected):
    assert label(facts.start("Intern", sentences(sentence))) == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "We are a start-up founded in January 2020.",
        "Join our startup in Dubai this summer.",
        "Graduating between December 2027 and July 2028.",
        "Applications close on 30 November 2026.",
        "Mastercard powers economies and empowers people in 200+ countries.",
    ],
)
def test_start_is_not_invented(sentence):
    assert facts.start("Intern", sentences(sentence)) is None


def test_start_from_title_wins():
    fact = facts.start("Product Management Intern, Summer 2027 - Dubai", sentences("Starting June 2027."))
    assert (fact.label, fact.source) == ("Summer 2027", "title")


# --------------------------------------------------------------- duration


@pytest.mark.parametrize(
    "sentence, expected",
    [
        ("Available to work full-time for 10-12 weeks starting June 2027", "10 to 12 weeks"),
        ("The internship starts mid-June 2027 and has a duration of 12 weeks.", "12 weeks"),
        ("You should be available for 3 to 6 months, full time (40h/week).", "3 to 6 months"),
        ("Internship length is 3 to 6 months, full-time.", "3 to 6 months"),
        ("is now inviting applications for internships of 6 months duration in our Business Intelligence department", "6 months"),
        ("Over the course of this 18-month program, you'll build specialized expertise.", "18 months"),
        ("This is a six month internship.", "6 months"),
        ("The placement lasts one month.", "1 month"),
    ],
)
def test_duration_is_read(sentence, expected):
    assert label(facts.duration("Intern", sentences(sentence))) == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "At least 2 years of experience in a similar internship programme.",
        "Graduated within the last 12 months from a recognised programme.",
        "A three month probation period applies to this contract.",
        "We have grown 40% in 6 months.",
        "The prescription must be issued within 3 months of the internship.",
    ],
)
def test_duration_is_not_invented(sentence):
    assert facts.duration("Intern", sentences(sentence)) is None


def test_duration_from_title():
    fact = facts.duration("Operations Trainee (UAE National Only) [6-month contract leading to full-time employment]", [])
    assert (fact.label, fact.source) == ("6 months", "title")


# ------------------------------------------------------------ eligibility


@pytest.mark.parametrize(
    "title, sentence, expected",
    [
        ("AWS Commercial Sales Internship", "Candidates must be a UAE National with a Family Book, and must be currently enrolled.", "nationals_only"),
        ("Operations Trainee (UAE National Only)", "", "nationals_only"),
        ("Associate Data Scientist - Builders Program - (Emirati National)", "", "nationals_only"),
        ("Graduate Trainee", "This programme is open to UAE nationals only.", "nationals_only"),
        ("Graduate Trainee", "This role supports our Emiratisation strategy.", "nationals_only"),
        ("Product Management Intern, Summer 2027 (UAE Nationals Preferred)", "", "nationals_preferred"),
        ("Intern", "Preference will be given to UAE nationals.", "nationals_preferred"),
        ("Intern", "We welcome applications from all nationalities.", "open"),
        ("Intern", "Visa sponsorship is provided for the successful candidate.", "open"),
        ("Intern", "Candidates must have a valid UAE residence visa.", "own_visa"),
        ("Intern", "Visa sponsorship is not available for this role.", "own_visa"),
        ("Intern", "You must be on your own visa or a family sponsored visa.", "own_visa"),
    ],
)
def test_eligibility_is_read(title, sentence, expected):
    fact = facts.eligibility(title, sentences(sentence))
    assert fact is not None and fact.value == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "You will work with clients across the UAE and Saudi Arabia.",
        "We serve national and international customers.",
        "Mastercard is an inclusive equal opportunity employer.",
        "Experience with Emirates NBD integrations is a plus.",
    ],
)
def test_eligibility_is_not_invented(sentence):
    assert facts.eligibility("Software Intern", sentences(sentence)) is None


def test_nationals_only_beats_a_later_open_sentence():
    text = "This programme is for UAE nationals only. Our team includes all nationalities."
    assert facts.eligibility("Trainee", sentences(text)).value == "nationals_only"


# -------------------------------------------------------------------- pay


@pytest.mark.parametrize(
    "sentence, expected",
    [
        ("This is an unpaid internship.", "Unpaid"),
        ("Please note there is no stipend for this role.", "Unpaid"),
        ("A monthly stipend of AED 3,000 is provided.", "AED 3,000 a month"),
        ("Stipend: 2500 AED per month.", "AED 2,500 a month"),
        ("Salary range AED 4,000 - 6,000 monthly.", "AED 4,000 to 6,000 a month"),
        ("Compensation $100,000 - $140,000/year, prorated for the length of the internship", "USD 100,000 to 140,000 a year"),
        ("This paid internship gives you the chance to take on a real business project.", "Paid, amount not stated"),
        ("Competitive pay", "Paid, amount not stated"),
        ("We offer a competitive salary and benefits.", "Paid, amount not stated"),
    ],
)
def test_pay_is_read(sentence, expected):
    assert label(facts.pay(sentences(sentence))) == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "Our platform processes AED 2,000,000 in payments every day.",
        "You will pay attention to detail.",
        "We have 3,000 employees and paid time off.",
    ],
)
def test_pay_is_not_invented(sentence):
    assert facts.pay(sentences(sentence)) is None


# ------------------------------------------------------------------ stage


@pytest.mark.parametrize(
    "sentence, expected",
    [
        ("Penultimate Year Students currently enrolled in a Bachelor's or Master's degree", "Penultimate-year students (Bachelor's, Master's)"),
        ("In the last year of a Bachelor's or Master's degree in Electrical Engineering", "Final-year students (Bachelor's, Master's)"),
        ("Recently graduated or enrolled in the final semester, with a Bachelor's Degree in a relevant field", "Final-year students (Bachelor's)"),
        ("Currently pursuing a Bachelor's, Master's, or PhD degree in Computer Science", "Current students (Bachelor's, Master's, PhD)"),
        ("Designed for recent graduates and early-career talent with up to two years of experience", "Recent graduates"),
        ("A Bachelor's degree in AI, Statistics, Math or a related qualification", "Bachelor's"),
    ],
)
def test_stage_is_read(sentence, expected):
    assert label(facts.stage(sentences(sentence))) == expected


def test_stage_is_not_invented():
    assert facts.stage(sentences("You will master our tools and work with the BS team.")) is None


# ------------------------------------------------------------------- mode


@pytest.mark.parametrize(
    "feed, sentence, expected",
    [
        ("onsite", "", "On site"),
        ("Hybrid", "", "Hybrid"),
        (None, "This position requires the intern to report to work on site daily.", "On site"),
        (None, "This role is on-site in our Dubai office.", "On site"),
        (None, "Work model: Onsite", "On site"),
        (None, "Hybrid working, three days in the office.", "Hybrid"),
        (None, "This internship is fully remote.", "Remote"),
    ],
)
def test_mode_is_read(feed, sentence, expected):
    assert label(facts.mode(feed, sentences(sentence))) == expected


@pytest.mark.parametrize(
    "sentence",
    [
        "Interacting with third-party vendors and contractors working on site",
        "Work alongside third-party vendors and contractors onsite.",
        "You will monitor remote sensors across the region.",
        "Your work will ensure that the data center's systems operate at 100% availability.",
    ],
)
def test_mode_is_not_invented(sentence):
    assert facts.mode(None, sentences(sentence)) is None


# --------------------------------------------------------------- deadline


def test_deadline_is_read():
    assert label(facts.deadline(sentences("Applications close on 30 November 2026."))) == "30 November 2026"
    assert label(facts.deadline(sentences("Apply by December 5, 2026 to be considered."))) == "December 5, 2026"
    assert facts.deadline(sentences("We were founded on 30 November 2019.")) is None


# ----------------------------------------------------------------- fields


@pytest.mark.parametrize(
    "title, department, expected",
    [
        ("Machine Learning - Intern", None, "AI and machine learning"),
        ("AI Engineer Internship - LLM Data", "Engineering", "AI and machine learning"),
        ("Data Analyst - Intern", None, "Data and analytics"),
        ("Intern, Technical Program Management", None, "Software engineering"),
        ("Data Center Technician - 2027 Internship", None, "IT, cloud and security"),
        ("Merchant Acquisition Intern", None, "Sales and business development"),
        ("Animator Intern", None, "Product and design"),
        ("Graduate Trainee", "Finance", "Finance and accounting"),
        ("Tamara Internship Program", None, "Other"),
    ],
)
def test_fields(title, department, expected):
    assert facts.fields(title, department)[0] == expected


def test_every_fact_carries_its_sentence():
    text = "About us.\nThe internship starts mid-June 2027 and has a duration of 12 weeks.\nThis paid internship is based in Dubai."
    found = facts.read("Sales Internship", text)
    assert set(found) == {"pay", "duration", "start"}
    for fact in found.values():
        assert fact.evidence in text
