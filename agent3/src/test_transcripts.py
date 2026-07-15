from analyzer import analyze_transcript
from semantic_analyzer import semantic_analysis
from llm_analyzer import analyze_with_llm
from decision_engine import make_final_decision

import json


test_cases = {

    "Digital Arrest": """
Hello sir, I am calling from Cyber Crime Department.
Your Aadhaar card has been linked to illegal activities.
You are involved in money laundering.
Stay on the call and press one for video verification.
""",


    "Bank Fraud": """
Dear customer, your bank account will be blocked today.
There was a suspicious transaction.
Please share your OTP and debit card details to verify your account.
""",


    "KYC Scam": """
Your KYC has expired.
Your SIM card will be blocked.
Download this application and update your PAN card details immediately.
""",


    "Courier Scam": """
Your parcel from Mumbai customs has been seized.
Illegal items were found in your package.
Pay the customs charges to release your parcel.
""",


    "Investment Scam": """
Invest only today and get guaranteed double returns.
Our crypto investment plan gives 50 percent profit every week.
Transfer money to start earning.
""",


    "Lottery Scam": """
Congratulations!
You have won a lottery prize of 25 lakh rupees.
Pay processing fees to claim your reward.
""",


    "Job Scam": """
You have been selected for a work from home job.
Pay registration fees to confirm your position.
""",


    "Normal Call": """
Hello, your food order has been delivered.
Thank you for using our service.
"""
}



for name, transcript in test_cases.items():

    print("\n")
    print("="*60)
    print("TEST CASE:", name)
    print("="*60)


    keyword_result = analyze_transcript(transcript)

    semantic_result = semantic_analysis(transcript)

    llm_result = analyze_with_llm(transcript)


    final_result = make_final_decision(
        keyword_result,
        semantic_result,
        llm_result
    )


    print(json.dumps(
        {
            "keyword_prediction":
                keyword_result["scam_type"],

            "semantic_prediction":
                semantic_result["predicted_scam"],

            "llm_prediction":
                llm_result["scam_type"],

            "FINAL":
                final_result["final_prediction"],

            "RISK":
                final_result["risk_level"],

            "SCORE":
                final_result["final_risk_score"],

            "CONFIDENCE":
                final_result["confidence"]
        },
        indent=4
    ))