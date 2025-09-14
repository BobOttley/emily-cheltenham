# Cheltenham College – Static QA config (AUTO-GENERATED, aggressive)
# Do not edit by hand. Re-run generate_static_qa.py to refresh.
from typing import Dict, List

SITE_ROOT = "https://www.cheltenhamcollege.org"

# url_mapping anchors (core pages). Auto-generated from mapping + defaults in generator.
PAGE_LINKS: Dict[str, str] = {
    "admissions": "https://www.cheltenhamcollege.org/admissions/",
    "anti-bullying": "https://www.cheltenhamcollege.org/wp-content/uploads/2025/02/Modern-Slavery-Statement.pdf",
    "behaviour policy": "https://www.cheltenhamcollege.org/wp-content/uploads/2025/02/Modern-Slavery-Statement.pdf",
    "boarding": "https://www.cheltenhamcollege.org/college/houses/",
    "calendar": "https://www.cheltenhamcollege.org/key-information-for-parents/term-dates/",
    "co-curricular": "https://www.cheltenhamcollege.org/college/co-curricular/",
    "complaints": "https://www.cheltenhamcollege.org/wp-content/uploads/2025/02/Modern-Slavery-Statement.pdf",
    "contact": "https://www.cheltenhamcollege.org/contact-us/",
    "cookies": "https://www.cheltenhamcollege.org/",
    "destinations": "https://www.cheltenhamcollege.org/",
    "enquiry": "https://www.cheltenhamcollege.org/contact-us/",
    "fees": "https://www.cheltenhamcollege.org/admissions/fees/",
    "governors": "https://www.cheltenhamcollege.org/",
    "home": "https://www.cheltenhamcollege.org/",
    "homepage": "https://www.cheltenhamcollege.org/",
    "isi report": "https://www.cheltenhamcollege.org/wp-content/uploads/2025/02/Modern-Slavery-Statement.pdf",
    "main page": "https://www.cheltenhamcollege.org/",
    "music": "https://www.cheltenhamcollege.org/individual-music-lessons/",
    "open events": "https://www.cheltenhamcollege.org/admissions/visit-us/",
    "pastoral": "https://www.cheltenhamcollege.org/college/health-wellbeing/",
    "policies": "https://www.cheltenhamcollege.org/about-us/aims-policies/",
    "privacy": "https://www.cheltenhamcollege.org/privacy-terms/",
    "results": "https://www.cheltenhamcollege.org/college/2025-results/",
    "safeguarding": "https://www.cheltenhamcollege.org/wp-content/uploads/2025/02/Modern-Slavery-Statement.pdf",
    "scholarships": "https://www.cheltenhamcollege.org/scholarships-key-dates/",
    "send": "https://www.cheltenhamcollege.org/health-promotion/",
    "sixth form": "https://www.cheltenhamcollege.org/college/sixth-form/",
    "sport": "https://www.cheltenhamcollege.org/college/sport/",
    "staff": "https://www.cheltenhamcollege.org/about-us/our-staff/",
    "head":  "https://www.cheltenhamcollege.org/about-us/our-staff/",
    "subjects": "https://www.cheltenhamcollege.org/college/lower-college-curriculum/",
    "term dates": "https://www.cheltenhamcollege.org/key-information-for-parents/term-dates/",
    "transport": "https://www.cheltenhamcollege.org/key-information-for-parents/bus-service/",
    "uniform": "https://www.cheltenhamcollege.org/key-information-for-parents/uniform/",
}

def L(key: str) -> str:
    return PAGE_LINKS.get(key, SITE_ROOT)


STATIC_QA_LIST = [
    {
        "key": "admissions",
        "language": "en",
        "answer": "Cheltenham College admissions information, entry process and who to contact.",
        "url": L("admissions"),
        "label": "Admissions",
        "variants": ["admissions", "apply", "join", "application", "registration", "how to apply", "entry process"]
    },
    {
        "key": "enquiry",
        "language": "en",
        "answer": "Send an enquiry to our Admissions team and we’ll be in touch with next steps.",
        "url": L("enquiry"),
        "label": "Send an enquiry",
        "variants": ["enquiry", "enquire", "contact admissions", "ask a question", "request information"]
    },
    {
        "key": "open events",
        "language": "en",
        "answer": "We host open mornings and visit opportunities throughout the year. Choose a date and register online.",
        "url": L("open events"),
        "label": "Open events",
        "variants": ["open morning", "open day", "visit", "tour", "open evening"]
    },
    {
    "key": "fees_vat",
    "language": "en",
    "answer": "School fees at Cheltenham College **do include VAT** in line with current UK regulations. Please see our [fees page](https://www.cheltenhamcollege.org/admissions/fees/) for details of charges.",
    "url": L("fees"),
    "label": "Fees and VAT",
    "variants": ["vat", "vat on fees", "fees vat", "fees include vat", "school fees vat", "do fees include vat"]
},

    {
        "key": "scholarships",
        "language": "en",
        "answer": "We offer a range of scholarships and bursaries. Guidance and criteria are available online.",
        "url": L("scholarships"),
        "label": "Scholarships & bursaries",
        "variants": ["scholarships", "bursaries", "financial aid", "awards"]
    },
    {
        "key": "term dates",
        "language": "en",
        "answer": "Term dates and the school calendar are available online.",
        "url": L("term dates"),
        "label": "Term dates",
        "variants": ["term dates", "calendar", "half term", "holiday dates"]
    },
    {
        "key": "sixth form",
        "language": "en",
        "answer": "Explore Sixth Form life, subjects and opportunities.",
        "url": L("sixth form"),
        "label": "Sixth Form",
        "variants": ["sixth form", "a level", "a-level"]
    },
    {
        "key": "subjects",
        "language": "en",
        "answer": "Find details of subjects and the academic programme.",
        "url": L("subjects"),
        "label": "Subjects & curriculum",
        "variants": ["subjects", "curriculum", "departments", "academic"]
    },
    {
        "key": "pastoral",
        "language": "en",
        "answer": "Pastoral care and wellbeing information.",
        "url": L("pastoral"),
        "label": "Pastoral care",
        "variants": ["pastoral", "wellbeing", "support"]
    },
    {
        "key": "boarding",
        "language": "en",
        "answer": "Cheltenham College offers boarding and day places. Read about our boarding information and principles.",
        "url": L("boarding"),
        "label": "Boarding",
        "variants": ["boarding", "houses", "boarder", "boarding principles"]
    },
    {
        "key": "safeguarding",
        "language": "en",
        "answer": "Read about safeguarding and our policies.",
        "url": L("safeguarding"),
        "label": "Safeguarding",
        "variants": ["safeguarding", "child protection"]
    },
    {
        "key": "send",
        "language": "en",
        "answer": "Information about learning support (SEND).",
        "url": L("send"),
        "label": "Learning support (SEND)",
        "variants": ["send", "sen", "learning support", "academic support", "eal"]
    },
    {
        "key": "behaviour policy",
        "language": "en",
        "answer": "Read the behaviour policy.",
        "url": L("behaviour policy"),
        "label": "Behaviour policy",
        "variants": ["behaviour", "discipline", "code of conduct"]
    },
    {
        "key": "anti-bullying",
        "language": "en",
        "answer": "Read the anti-bullying policy.",
        "url": L("anti-bullying"),
        "label": "Anti-bullying policy",
        "variants": ["anti bullying", "bullying"]
    },
    {
        "key": "complaints",
        "language": "en",
        "answer": "Read the complaints policy and procedure.",
        "url": L("complaints"),
        "label": "Complaints policy",
        "variants": ["complaints", "complaint procedure"]
    },
    {
        "key": "isi report",
        "language": "en",
        "answer": "Read the latest inspection (ISI) report.",
        "url": L("isi report"),
        "label": "ISI report",
        "variants": ["isi", "inspection report", "isi inspection"]
    },
    {
        "key": "co-curricular",
        "language": "en",
        "answer": "Co-curricular opportunities, clubs and activities.",
        "url": L("co-curricular"),
        "label": "Co-curricular",
        "variants": ["co-curricular", "clubs", "activities", "societies"]
    },
    {
        "key": "sport",
        "language": "en",
        "answer": "Sport at school, including fixtures and programmes.",
        "url": L("sport"),
        "label": "Sport",
        "variants": ["sport", "games", "pe", "fixtures"]
    },
    {
        "key": "music",
        "language": "en",
        "answer": "Music opportunities and ensembles.",
        "url": L("music"),
        "label": "Music",
        "variants": ["music", "choir", "orchestra"]
    },
    {
        "key": "results",
        "language": "en",
        "answer": "Recent academic results and headline outcomes.",
        "url": L("results"),
        "label": "Results",
        "variants": ["results", "exam results", "academic results", "grades"]
    },
    {
        "key": "destinations",
        "language": "en",
        "answer": "Leavers’ destinations and university entries.",
        "url": L("destinations"),
        "label": "Leavers’ destinations",
        "variants": ["destinations", "university destinations", "leavers"]
    },
    {
        "key": "uniform",
        "language": "en",
        "answer": "Uniform information and outfitters.",
        "url": L("uniform"),
        "label": "Uniform",
        "variants": ["uniform", "outfitters"]
    },
    {
        "key": "transport",
        "language": "en",
        "answer": "Transport routes and travel information.",
        "url": L("transport"),
        "label": "Transport",
        "variants": ["transport", "bus", "coach", "minibus"]
    },
    {
        "key": "governors",
        "language": "en",
        "answer": "Meet the Governors / Trustees.",
        "url": L("governors"),
        "label": "Governors",
        "variants": ["governors", "board of governors", "trustees"]
    },
    {
        "key": "staff",
        "language": "en",
        "answer": "Find staff information and contacts.",
        "url": L("staff"),
        "label": "Staff",
        "variants": ["staff", "staff list", "directory", "teachers"]
    },
    {
        "key": "policies",
        "language": "en",
        "answer": "Browse all policies.",
        "url": L("policies"),
        "label": "Policies",
        "variants": ["policies", "policy list"]
    },
    {
        "key": "privacy",
        "language": "en",
        "answer": "Read our Privacy Policy.",
        "url": L("privacy"),
        "label": "Privacy Policy",
        "variants": ["privacy", "gdpr", "data protection"]
    },
    {
        "key": "cookies",
        "language": "en",
        "answer": "Cookie Policy.",
        "url": L("cookies"),
        "label": "Cookies",
        "variants": ["cookies", "cookie policy"]
    },
    {
        "key": "contact",
        "language": "en",
        "answer": "Get in touch with the school team.",
        "url": L("contact"),
        "label": "Contact",
        "variants": ["contact", "contact us", "how to find us", "phone number", "email"]
    },
    {
        "key": "policy::13 scholarship application form 2026",
        "language": "en",
        "answer": "Read the 13 Scholarship Application Form 2026.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/01090352/13-Scholarship-Application-Form-2026.pdf",
        "label": "13 Scholarship Application Form 2026",
        "variants": ["policy scholarship application form", "13 scholarship application form 2026", "scholarship application form"]
    },
    {
        "key": "policy::16 scholarship application form 2025",
        "language": "en",
        "answer": "Read the 16 Scholarship Application Form 2025.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/01090417/16-Scholarship-Application-Form-2025.pdf",
        "label": "16 Scholarship Application Form 2025",
        "variants": ["16 scholarship application form 2025", "policy scholarship application form", "scholarship application form"]
    },
    {
        "key": "policy::2023 overseas schools 1",
        "language": "en",
        "answer": "Read the 2023 Overseas Schools 1.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/11/27145407/2023-Overseas-Schools-1.pdf",
        "label": "2023 Overseas Schools 1",
        "variants": ["policy overseas schools", "2023 overseas schools 1", "overseas schools"]
    },
    {
        "key": "policy::admissions policy cc",
        "language": "en",
        "answer": "Read the Admissions Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/24143341/Admissions-Policy-CC.pdf",
        "label": "Admissions Policy Cc",
        "variants": ["admissions  cc", "admissions policy cc", "policy admissions cc", "admissions cc"]
    },
    {
        "key": "policy::anti bullying p policy",
        "language": "en",
        "answer": "Read the Anti Bullying P Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/24143508/Anti-Bullying-P.pdf",
        "label": "Anti Bullying P Policy",
        "variants": ["anti bullying p policy", "anti bullying p", "policy anti bullying p"]
    },
    {
        "key": "policy::anti bullying policy c",
        "language": "en",
        "answer": "Read the Anti Bullying Policy C.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/24143718/Anti-Bullying-Policy-C.pdf",
        "label": "Anti Bullying Policy C",
        "variants": ["anti bullying c", "anti bullying  c", "anti bullying policy c", "policy anti bullying c"]
    },
    {
        "key": "policy::assistant camp co ordinator",
        "language": "en",
        "answer": "Read the Assistant Camp Co Ordinator.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/08/27134315/Assistant-Camp-Co-Ordinator.pdf",
        "label": "Assistant Camp Co Ordinator",
        "variants": ["policy assistant camp co ordinator", "assistant camp co ordinator"]
    },
    {
        "key": "policy::attendance and registration policy c",
        "language": "en",
        "answer": "Read the Attendance and Registration Policy C.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/08143223/Attendance-and-Registration-Policy-C.pdf",
        "label": "Attendance and Registration Policy C",
        "variants": ["attendance and registration c", "policy attendance and registration c", "attendance and registration  c", "attendance and registration policy c"]
    },
    {
        "key": "policy::attendance and registration policy p",
        "language": "en",
        "answer": "Read the Attendance and Registration Policy P.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/09090834/Attendance-and-Registration-Policy-P-.pdf",
        "label": "Attendance and Registration Policy P",
        "variants": ["attendance and registration p", "policy attendance and registration p", "attendance and registration  p", "attendance and registration policy p"]
    },
    {
        "key": "policy::boarding principles p",
        "language": "en",
        "answer": "Read the Boarding Principles P.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/08/06145039/Boarding-Principles-P.pdf",
        "label": "Boarding Principles P",
        "variants": ["policy boarding principles p", "boarding principles p"]
    },
    {
        "key": "policy::bursary policy cc",
        "language": "en",
        "answer": "Read the Bursary Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/09133612/Bursary-Policy-CC.pdf",
        "label": "Bursary Policy Cc",
        "variants": ["bursary policy cc", "bursary cc", "policy bursary cc", "bursary  cc"]
    },
    {
        "key": "policy::bus timetable",
        "language": "en",
        "answer": "Read the Bus Timetable.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/09/19091752/Bus-Timetable.pdf",
        "label": "Bus Timetable",
        "variants": ["bus timetable", "policy bus timetable"]
    },
    {
        "key": "policy::cc sept 23",
        "language": "en",
        "answer": "Read the Cc Sept 23.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/03/30141237/CC-Sept-23.pdf",
        "label": "Cc Sept 23",
        "variants": ["cc sept 23", "cc sept", "policy cc sept"]
    },
    {
        "key": "policy::cc279 isi college 2023 digi",
        "language": "en",
        "answer": "Read the Cc279 Isi College 2023 Digi.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/06/21140127/CC279-ISI-College-2023-Digi.pdf",
        "label": "Cc279 Isi College 2023 Digi",
        "variants": ["cc279 isi college 2023 digi", "policy cc isi college digi", "cc isi college digi"]
    },
    {
        "key": "policy::cctv policy cc",
        "language": "en",
        "answer": "Read the Cctv Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/11/27093645/CCTV-Policy-CC.pdf",
        "label": "Cctv Policy Cc",
        "variants": ["cctv cc", "cctv  cc", "policy cctv cc", "cctv policy cc"]
    },
    {
        "key": "policy::cctv privacy impact assessment cc policy",
        "language": "en",
        "answer": "Read the Cctv Privacy Impact Assessment Cc Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/11/27093718/CCTV-Privacy-Impact-Assessment-CC.pdf",
        "label": "Cctv Privacy Impact Assessment Cc Policy",
        "variants": ["cctv privacy impact assessment cc policy", "cctv privacy impact assessment cc", "policy cctv privacy impact assessment cc"]
    },
    {
        "key": "policy::cheltenham college isi report",
        "language": "en",
        "answer": "Read the Cheltenham College Isi Report.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/05/24135508/Cheltenham-College-ISI-Report.pdf",
        "label": "Cheltenham College Isi Report",
        "variants": ["policy cheltenham college isi report", "cheltenham college isi report"]
    },
    {
        "key": "policy::cheltenham college preparatory school eqi report v5 2023 05 231",
        "language": "en",
        "answer": "Read the Cheltenham College Preparatory School Eqi Report V5 2023 05 231.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/05/24135533/Cheltenham-College-Preparatory-School-EQI-report-v5-2023-05-231.pdf",
        "label": "Cheltenham College Preparatory School Eqi Report V5 2023 05 231",
        "variants": ["cheltenham college preparatory school eqi report v5 2023 05 231", "policy cheltenham college preparatory school eqi report v", "cheltenham college preparatory school eqi report v"]
    },
    {
        "key": "policy::cheltenham prep uniform list 2023",
        "language": "en",
        "answer": "Read the Cheltenham Prep Uniform List 2023.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/10/27142315/Cheltenham-Prep-Uniform-List-2023.pdf",
        "label": "Cheltenham Prep Uniform List 2023",
        "variants": ["policy cheltenham prep uniform list", "cheltenham prep uniform list", "cheltenham prep uniform list 2023"]
    },
    {
        "key": "policy::climate action plan 2024.25",
        "language": "en",
        "answer": "Read the Climate Action Plan 2024.25.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/11/08101137/Climate-Action-Plan-2024.25.pdf",
        "label": "Climate Action Plan 2024.25",
        "variants": ["policy climate action plan", "climate action plan", "climate action plan 2024.25"]
    },
    {
        "key": "policy::climate action report 2023 2024",
        "language": "en",
        "answer": "Read the Climate Action Report 2023 2024.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/09/10153304/Climate-Action-Report-2023-2024.pdf",
        "label": "Climate Action Report 2023 2024",
        "variants": ["climate action report 2023 2024", "climate action report", "policy climate action report"]
    },
    {
        "key": "policy::college additional costs 2025 26",
        "language": "en",
        "answer": "Read the College Additional Costs 2025 26.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/29124046/College-Additional-Costs-2025-26.pdf",
        "label": "College Additional Costs 2025 26",
        "variants": ["college additional costs 2025 26", "college additional costs", "policy college additional costs"]
    },
    {
        "key": "policy::college dining hall menu autumn 2025",
        "language": "en",
        "answer": "Read the College Dining Hall Menu Autumn 2025.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/01144432/College-Dining-Hall-Menu-Autumn-2025.pdf",
        "label": "College Dining Hall Menu Autumn 2025",
        "variants": ["college dining hall menu autumn", "college dining hall menu autumn 2025", "policy college dining hall menu autumn"]
    },
    {
        "key": "policy::college sports kit 2022 fva 180322",
        "language": "en",
        "answer": "Read the College Sports Kit 2022 Fva 180322.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2022/03/26061259/College-Sports-Kit-2022-FVA-180322.pdf",
        "label": "College Sports Kit 2022 Fva 180322",
        "variants": ["policy college sports kit fva", "college sports kit 2022 fva 180322", "college sports kit fva"]
    },
    {
        "key": "policy::college timeline anne cadbury room18",
        "language": "en",
        "answer": "Read the College Timeline Anne Cadbury Room18.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/08/30121907/College-Timeline-Anne-Cadbury-Room18.pdf",
        "label": "College Timeline Anne Cadbury Room18",
        "variants": ["college timeline anne cadbury room", "policy college timeline anne cadbury room", "college timeline anne cadbury room18"]
    },
    {
        "key": "policy::curriculum policy c",
        "language": "en",
        "answer": "Read the Curriculum Policy C.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/10/08135850/Curriculum-Policy-C.pdf",
        "label": "Curriculum Policy C",
        "variants": ["policy curriculum c", "curriculum c", "curriculum policy c", "curriculum  c"]
    },
    {
        "key": "policy::curriculum policy p",
        "language": "en",
        "answer": "Read the Curriculum Policy P.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/10/03143650/Curriculum-Policy-P.pdf",
        "label": "Curriculum Policy P",
        "variants": ["curriculum policy p", "policy curriculum p", "curriculum  p", "curriculum p"]
    },
    {
        "key": "policy::dates and deadlines",
        "language": "en",
        "answer": "Read the Dates and Deadlines.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2022/09/23142756/Dates-and-Deadlines.pdf",
        "label": "Dates and Deadlines",
        "variants": ["dates and deadlines", "policy dates and deadlines"]
    },
    {
        "key": "policy::dining hall spring menu",
        "language": "en",
        "answer": "Read the Dining Hall Spring Menu.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/03/06161644/Dining-Hall-Spring-menu.pdf",
        "label": "Dining Hall Spring Menu",
        "variants": ["policy dining hall spring menu", "dining hall spring menu"]
    },
    {
        "key": "policy::eal policy c",
        "language": "en",
        "answer": "Read the Eal Policy C.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/09090207/EAL-Policy-C.pdf",
        "label": "Eal Policy C",
        "variants": ["policy eal c", "eal c", "eal  c", "eal policy c"]
    },
    {
        "key": "policy::eal policy p",
        "language": "en",
        "answer": "Read the Eal Policy P.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/10080227/EAL-Policy-P.pdf",
        "label": "Eal Policy P",
        "variants": ["eal  p", "policy eal p", "eal policy p", "eal p"]
    },
    {
        "key": "policy::energy policy cc",
        "language": "en",
        "answer": "Read the Energy Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/02/29155318/Energy-Policy-CC.pdf",
        "label": "Energy Policy Cc",
        "variants": ["energy cc", "energy policy cc", "energy  cc", "policy energy cc"]
    },
    {
        "key": "policy::evensong summer 2023",
        "language": "en",
        "answer": "Read the Evensong Summer 2023.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/05/04125841/Evensong-Summer-2023.pdf",
        "label": "Evensong Summer 2023",
        "variants": ["evensong summer", "evensong summer 2023", "policy evensong summer"]
    },
    {
        "key": "policy::fees supervisor july 25",
        "language": "en",
        "answer": "Read the Fees Supervisor July 25.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/01152139/Fees-Supervisor-July-25.pdf",
        "label": "Fees Supervisor July 25",
        "variants": ["fees supervisor july", "fees supervisor july 25", "policy fees supervisor july"]
    },
    {
        "key": "policy::first aid policy cc",
        "language": "en",
        "answer": "Read the First Aid Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/03/17141231/First-Aid-Policy-CC.pdf",
        "label": "First Aid Policy Cc",
        "variants": ["first aid  cc", "first aid cc", "policy first aid cc", "first aid policy cc"]
    },
    {
        "key": "policy::fourth and fifth form uniform list",
        "language": "en",
        "answer": "Read the Fourth and Fifth Form Uniform List.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/12134950/Fourth-and-Fifth-Form-Uniform-List.pdf",
        "label": "Fourth and Fifth Form Uniform List",
        "variants": ["fourth and fifth form uniform list", "policy fourth and fifth form uniform list"]
    },
    {
        "key": "policy::fv identity introduction",
        "language": "en",
        "answer": "Read the Fv Identity Introduction.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2022/02/26061507/FV-Identity-Introduction.pdf",
        "label": "Fv Identity Introduction",
        "variants": ["policy fv identity introduction", "fv identity introduction"]
    },
    {
        "key": "policy::gender pay gap statement 2024 policy",
        "language": "en",
        "answer": "Read the Gender Pay Gap Statement 2024 Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/02/04120247/Gender-Pay-Gap-Statement-2024.pdf",
        "label": "Gender Pay Gap Statement 2024 Policy",
        "variants": ["gender pay gap statement policy", "policy gender pay gap statement", "gender pay gap statement", "gender pay gap statement 2024 policy"]
    },
    {
        "key": "policy::guardianship policy cc",
        "language": "en",
        "answer": "Read the Guardianship Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/08/29154156/Guardianship-Policy-CC.pdf",
        "label": "Guardianship Policy Cc",
        "variants": ["policy guardianship cc", "guardianship cc", "guardianship policy cc", "guardianship  cc"]
    },
    {
        "key": "policy::health centre handbook 2023 policy",
        "language": "en",
        "answer": "Read the Health Centre Handbook 2023 Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/04/03131918/Health-Centre-Handbook-2023.pdf",
        "label": "Health Centre Handbook 2023 Policy",
        "variants": ["policy health centre handbook", "health centre handbook policy", "health centre handbook", "health centre handbook 2023 policy"]
    },
    {
        "key": "policy::health and safety cc policy",
        "language": "en",
        "answer": "Read the Health and Safety Cc Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/05/15085800/Health-and-Safety-CC.pdf",
        "label": "Health and Safety Cc Policy",
        "variants": ["health and safety cc policy", "policy health and safety cc", "health and safety cc"]
    },
    {
        "key": "policy::house principles c",
        "language": "en",
        "answer": "Read the House Principles C.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/10/15115539/House-Principles-C.pdf",
        "label": "House Principles C",
        "variants": ["policy house principles c", "house principles c"]
    },
    {
        "key": "policy::humanities teacher maternity cover january 2026",
        "language": "en",
        "answer": "Read the Humanities Teacher Maternity Cover January 2026.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/02122633/Humanities-Teacher-Maternity-Cover-January-2026.pdf",
        "label": "Humanities Teacher Maternity Cover January 2026",
        "variants": ["policy humanities teacher maternity cover january", "humanities teacher maternity cover january", "humanities teacher maternity cover january 2026"]
    },
    {
        "key": "policy::independent guidance on criminal records disclosure policy",
        "language": "en",
        "answer": "Read the Independent Guidance on Criminal Records Disclosure Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/07/03153056/Independent-Guidance-on-Criminal-Records-Disclosure.pdf",
        "label": "Independent Guidance on Criminal Records Disclosure Policy",
        "variants": ["independent guidance on criminal records disclosure policy", "independent guidance on criminal records disclosure", "policy independent guidance on criminal records disclosure"]
    },
    {
        "key": "policy::isi cheltenham prep 2023 digi",
        "language": "en",
        "answer": "Read the Isi Cheltenham Prep 2023 Digi.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/06/21135852/ISI-Cheltenham-Prep-2023-DIGI.pdf",
        "label": "Isi Cheltenham Prep 2023 Digi",
        "variants": ["policy isi cheltenham prep digi", "isi cheltenham prep 2023 digi", "isi cheltenham prep digi"]
    },
    {
        "key": "policy::isi intergrated inspection report cheltenham college 2016",
        "language": "en",
        "answer": "Read the Isi Intergrated Inspection Report Cheltenham College 2016.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/29132507/ISI-Intergrated-Inspection-Report-Cheltenham-College-2016.pdf",
        "label": "Isi Intergrated Inspection Report Cheltenham College 2016",
        "variants": ["isi intergrated inspection report cheltenham college", "isi intergrated inspection report cheltenham college 2016", "policy isi intergrated inspection report cheltenham college"]
    },
    {
        "key": "policy::isi intergrated inspection report cheltenham prep 2016",
        "language": "en",
        "answer": "Read the Isi Intergrated Inspection Report Cheltenham Prep 2016.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/29132511/ISI-Intergrated-Inspection-Report-Cheltenham-Prep-2016.pdf",
        "label": "Isi Intergrated Inspection Report Cheltenham Prep 2016",
        "variants": ["isi intergrated inspection report cheltenham prep", "policy isi intergrated inspection report cheltenham prep", "isi intergrated inspection report cheltenham prep 2016"]
    },
    {
        "key": "policy::isi regulatory compliance inspection cheltenham college february 2019",
        "language": "en",
        "answer": "Read the Isi Regulatory Compliance Inspection Cheltenham College February 2019.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/29132512/ISI-Regulatory-Compliance-Inspection-Cheltenham-College-February-2019.pdf",
        "label": "Isi Regulatory Compliance Inspection Cheltenham College February 2019",
        "variants": ["isi regulatory compliance inspection cheltenham college february", "policy isi regulatory compliance inspection cheltenham college february", "isi regulatory compliance inspection cheltenham college february 2019"]
    },
    {
        "key": "policy::isi regulatory compliance inspection cheltenham prep february 2019",
        "language": "en",
        "answer": "Read the Isi Regulatory Compliance Inspection Cheltenham Prep February 2019.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/04/29132513/ISI-Regulatory-Compliance-Inspection-Cheltenham-Prep-February-2019.pdf",
        "label": "Isi Regulatory Compliance Inspection Cheltenham Prep February 2019",
        "variants": ["isi regulatory compliance inspection cheltenham prep february", "policy isi regulatory compliance inspection cheltenham prep february", "isi regulatory compliance inspection cheltenham prep february 2019"]
    },
    {
        "key": "policy::job description",
        "language": "en",
        "answer": "Read the Job Description.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/11104802/Job-Description.pdf",
        "label": "Job Description",
        "variants": ["job description", "policy job description"]
    },
    {
        "key": "policy::job description 1",
        "language": "en",
        "answer": "Read the Job Description 1.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/11111128/Job-Description-1.pdf",
        "label": "Job Description 1",
        "variants": ["job description", "job description 1", "policy job description"]
    },
    {
        "key": "policy::key child protection and safeguarding cc policy",
        "language": "en",
        "answer": "Read the Key Child Protection and Safeguarding Cc Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/09091013/Key-Child-Protection-and-Safeguarding-CC.pdf",
        "label": "Key Child Protection and Safeguarding Cc Policy",
        "variants": ["policy key child protection and safeguarding cc", "key child protection and safeguarding cc", "key child protection and safeguarding cc policy"]
    },
    {
        "key": "policy::key prep behaviour policy p",
        "language": "en",
        "answer": "Read the Key Prep Behaviour Policy P.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/02152901/Key-Prep-Behaviour-Policy-P.pdf",
        "label": "Key Prep Behaviour Policy P",
        "variants": ["key prep behaviour p", "policy key prep behaviour p", "key prep behaviour policy p", "key prep behaviour  p"]
    },
    {
        "key": "policy::key pupil behaviour policy c",
        "language": "en",
        "answer": "Read the Key Pupil Behaviour Policy C.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/30122253/Key-Pupil-Behaviour-Policy-C.pdf",
        "label": "Key Pupil Behaviour Policy C",
        "variants": ["key pupil behaviour  c", "key pupil behaviour c", "key pupil behaviour policy c", "policy key pupil behaviour c"]
    },
    {
        "key": "policy::learning support and sen policy cc",
        "language": "en",
        "answer": "Read the Learning Support and Sen Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/07/24104217/Learning-Support-and-SEN-Policy-CC.pdf",
        "label": "Learning Support and Sen Policy Cc",
        "variants": ["learning support and sen  cc", "learning support and sen policy cc", "learning support and sen cc", "policy learning support and sen cc"]
    },
    {
        "key": "policy::modern slavery statement policy",
        "language": "en",
        "answer": "Read the Modern Slavery Statement Policy.",
        "url": "https://www.cheltenhamcollege.org/wp-content/uploads/2025/02/Modern-Slavery-Statement.pdf",
        "label": "Modern Slavery Statement Policy",
        "variants": ["modern slavery statement", "modern slavery statement policy", "policy modern slavery statement"]
    },
    {
        "key": "policy::online safety policy cc",
        "language": "en",
        "answer": "Read the Online Safety Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/08/12130003/Online-Safety-Policy-CC.pdf",
        "label": "Online Safety Policy Cc",
        "variants": ["online safety  cc", "policy online safety cc", "online safety policy cc", "online safety cc"]
    },
    {
        "key": "policy::parents complaints policy cc",
        "language": "en",
        "answer": "Read the Parents Complaints Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/01/20165219/Parents-Complaints-Policy-CC.pdf",
        "label": "Parents Complaints Policy Cc",
        "variants": ["parents complaints  cc", "policy parents complaints cc", "parents complaints cc", "parents complaints policy cc"]
    },
    {
        "key": "policy::photography and film policy cc",
        "language": "en",
        "answer": "Read the Photography and Film Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/23121755/Photography-and-Film-Policy-CC.pdf",
        "label": "Photography and Film Policy Cc",
        "variants": ["photography and film policy cc", "policy photography and film cc", "photography and film  cc", "photography and film cc"]
    },
    {
        "key": "policy::policy",
        "language": "en",
        "answer": "Read the Policy.",
        "url": "https://www.cheltenhamcollege.org/privacy-terms/",
        "label": "Policy",
        "variants": ["", "policy", "policy policy"]
    },
    {
        "key": "policy::privacy notice for pupils parents guardians and cheltonian society members cc policy",
        "language": "en",
        "answer": "Read the Privacy Notice for Pupils Parents Guardians and Cheltonian Society Members Cc Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/10/08120719/Privacy-Notice-for-Pupils-Parents-Guardians-and-Cheltonian-Society-Members-CC.pdf",
        "label": "Privacy Notice for Pupils Parents Guardians and Cheltonian Society Members Cc Policy",
        "variants": ["privacy notice for pupils parents guardians and cheltonian society members cc policy", "policy privacy notice for pupils parents guardians and cheltonian society members cc", "privacy notice for pupils parents guardians and cheltonian society members cc"]
    },
    {
        "key": "policy::privacy notice for staff cc policy",
        "language": "en",
        "answer": "Read the Privacy Notice for Staff Cc Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/07/03135123/Privacy-Notice-for-Staff-CC.pdf",
        "label": "Privacy Notice for Staff Cc Policy",
        "variants": ["privacy notice for staff cc policy", "policy privacy notice for staff cc", "privacy notice for staff cc"]
    },
    {
        "key": "policy::procedure for purchase of ticket cistg 22 23 v1 policy",
        "language": "en",
        "answer": "Read the Procedure for Purchase of Ticket Cistg 22 23 V1 Policy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2022/09/26135132/Procedure-for-purchase-of-ticket-CISTG-22-23-V1-.pdf",
        "label": "Procedure for Purchase of Ticket Cistg 22 23 V1 Policy",
        "variants": ["policy procedure for purchase of ticket cistg v", "procedure for purchase of ticket cistg v policy", "procedure for purchase of ticket cistg v", "procedure for purchase of ticket cistg 22 23 v1 policy"]
    },
    {
        "key": "policy::recruitment policy cc",
        "language": "en",
        "answer": "Read the Recruitment Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/07/03135121/Recruitment-Policy-CC.pdf",
        "label": "Recruitment Policy Cc",
        "variants": ["policy recruitment cc", "recruitment policy cc", "recruitment cc", "recruitment  cc"]
    },
    {
        "key": "policy::recruitment social media checks policy v2 152",
        "language": "en",
        "answer": "Read the Recruitment Social Media Checks Policy V2 152.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2023/08/24075707/Recruitment-Social-Media-Checks-Policy-v2-152.pdf",
        "label": "Recruitment Social Media Checks Policy V2 152",
        "variants": ["recruitment social media checks  v", "policy recruitment social media checks v", "recruitment social media checks policy v2 152", "recruitment social media checks policy v", "recruitment social media checks v"]
    },
    {
        "key": "policy::relationships and sex education policy cc",
        "language": "en",
        "answer": "Read the Relationships and Sex Education Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/03/24090958/Relationships-and-Sex-Education-Policy-CC.pdf",
        "label": "Relationships and Sex Education Policy Cc",
        "variants": ["relationships and sex education cc", "policy relationships and sex education cc", "relationships and sex education policy cc", "relationships and sex education  cc"]
    },
    {
        "key": "policy::sixth form uniform list 2025",
        "language": "en",
        "answer": "Read the Sixth Form Uniform List 2025.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/07/08132948/Sixth-Form-Uniform-List-2025.pdf",
        "label": "Sixth Form Uniform List 2025",
        "variants": ["sixth form uniform list 2025", "policy sixth form uniform list", "sixth form uniform list"]
    },
    {
        "key": "policy::suspension and exclusion policy cc",
        "language": "en",
        "answer": "Read the Suspension and Exclusion Policy Cc.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/01/21101107/Suspension-and-Exclusion-Policy-CC.pdf",
        "label": "Suspension and Exclusion Policy Cc",
        "variants": ["suspension and exclusion  cc", "suspension and exclusion cc", "policy suspension and exclusion cc", "suspension and exclusion policy cc"]
    },
    {
        "key": "policy::sustainability strategy",
        "language": "en",
        "answer": "Read the Sustainability Strategy.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2024/08/22104533/Sustainability-Strategy-.pdf",
        "label": "Sustainability Strategy",
        "variants": ["policy sustainability strategy", "sustainability strategy"]
    },
    {
        "key": "policy::terms and conditions 2025 26",
        "language": "en",
        "answer": "Read the Terms and Conditions 2025 26.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/02141101/Terms-and-Conditions-2025-26.pdf",
        "label": "Terms and Conditions 2025 26",
        "variants": ["terms and conditions", "terms and conditions 2025 26", "policy terms and conditions"]
    },
    {
        "key": "policy::the muscat cheltonian 2021 22",
        "language": "en",
        "answer": "Read the The Muscat Cheltonian 2021 22.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2022/09/13103404/The-Muscat-Cheltonian-2021-22.pdf",
        "label": "The Muscat Cheltonian 2021 22",
        "variants": ["the muscat cheltonian", "the muscat cheltonian 2021 22", "policy the muscat cheltonian"]
    },
    {
        "key": "policy::third form uniform list",
        "language": "en",
        "answer": "Read the Third Form Uniform List.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/06/12134926/Third-Form-Uniform-List.pdf",
        "label": "Third Form Uniform List",
        "variants": ["third form uniform list", "policy third form uniform list"]
    },
    {
        "key": "policy::together community action and charity",
        "language": "en",
        "answer": "Read the Together Community Action and Charity.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2021/10/26062620/Together-Community-Action-and-Charity.pdf",
        "label": "Together Community Action and Charity",
        "variants": ["policy together community action and charity", "together community action and charity"]
    },
    {
        "key": "policy::together educational partnerships at cheltenham college",
        "language": "en",
        "answer": "Read the Together Educational Partnerships At Cheltenham College.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2021/10/26062621/Together-Educational-Partnerships-at-Cheltenham-College.pdf",
        "label": "Together Educational Partnerships At Cheltenham College",
        "variants": ["policy together educational partnerships at cheltenham college", "together educational partnerships at cheltenham college"]
    },
    {
        "key": "policy::valens menu autumn 2025",
        "language": "en",
        "answer": "Read the Valens Menu Autumn 2025.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/09/01144433/Valens-Menu-Autumn-2025.pdf",
        "label": "Valens Menu Autumn 2025",
        "variants": ["policy valens menu autumn", "valens menu autumn 2025", "valens menu autumn"]
    },
    {
        "key": "policy::valens spring menu",
        "language": "en",
        "answer": "Read the Valens Spring Menu.",
        "url": "https://cheltenham-college.s3.eu-west-2.amazonaws.com/wp-content/uploads/2025/03/06161703/Valens-Spring-Menu.pdf",
        "label": "Valens Spring Menu",
        "variants": ["policy valens spring menu", "valens spring menu"]
    },
    {
        "key": "sport::cross country",
        "language": "en",
        "answer": "Find information about Cross Country at Cheltenham College.",
        "url": "https://www.cheltenhamcollege.org/news/cheltenham-college-pupils-receive-excellent-gcse-results/",
        "label": "Cross Country",
        "variants": ["boys cross country", "cross country fixtures", "girls cross country", "cross country team", "cross country sport", "cross country", "cross country at cheltenham college"]
    },
    {
        "key": "sport::rugby",
        "language": "en",
        "answer": "Find information about Rugby at Cheltenham College.",
        "url": "https://www.cheltenhamcollege.org/news/a-visit-from-the-canadian-womens-rugby-team/",
        "label": "Rugby",
        "variants": ["rugby fixtures", "boys rugby", "rugby sport", "rugby team", "girls rugby", "rugby at cheltenham college", "rugby"]
    },
]
