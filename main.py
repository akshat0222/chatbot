from flask import Flask, render_template, request,jsonify
from google import generativeai as genai
from flask_cors import CORS
import pymysql

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# Configure Gemini
genai.configure(api_key="gemini_api_key") # replace your key
model = genai.GenerativeModel("gemini-2.5-flash")

# DB config (update with your credentials)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Akshat@123',
    'database': 'art_callcenter'
}

schema_description = """
The table `Leaddetails` stores information about potential clients and their journey through the sales funnel.
If the user asks a question that is not related to querying the Leads data — such as making updates, inserting data, deleting records, or asking irrelevant/non-SQL questions — do not generate a query. Instead, respond with:

"Sorry, I can only help with reading/querying data. Update or unrelated operations are not supported."

You are working with a table called `Leaddetails` in mysql server/database with the following columns:

- FirstName: First name of the lead.
- LastName: Last name of the lead.
- Origin: Source from where the lead originated.
- Phone: Lead’s primary phone number. This is a unique identifier for the lead.
- ProspectStage: Stage of the lead in the sales funnel (e.g., Converted, Closed, Contacted).
- CreatedOn: Timestamp when the lead was created.
- OwnerIdName: Name of the sales representative or lead owner.
- mx_Sub_Status: Indicates the sub-status of the lead. If the value is "Visit Done" or "TC Done", it means the lead has resulted in a footfall (i.e., the lead has physically visited or completed teleconsultation). Use this logic to identify footfall leads in queries.
- mx_Centre_Name: Name of the center/branch associated with the lead.
- Status: Represents the lead's validity. Possible values are "valid lead" and "invalid lead" (use full string values when filtering).
- media: The media source from which the lead was generated (e.g., Google Ads, Facebook Ads, Organic, Practo, Other).
- mx_Origin: The broader channel the lead belongs to (e.g., WOM, Digital, B2B, INT).
"""

def results_to_html(results):
    if not results:
        return "<p>No results found.</p>"

    headers = results[0].keys() if isinstance(results[0], dict) else range(len(results[0]))
    html = "<table border='1'><thead><tr>"
    for header in headers:
        html += f"<th>{header}</th>"
    html += "</tr></thead><tbody>"

    for row in results:
        html += "<tr>"
        for cell in (row.values() if isinstance(row, dict) else row):
            html += f"<td>{cell}</td>"
        html += "</tr>"

    html += "</tbody></table>"
    return html

def run_sql_query(sql):
    print("in ##############db")
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cursor.close()
        conn.close()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_query = data.get("user_query", "").strip()
    print(user_query)
    
    if not user_query:
        return jsonify({"error": "No user_query provided"}), 400

    try:
        # Use Gemini to generate SQL query
        prompt = f"""{schema_description}

            Generate a MySQL SELECT query based on the user question below:

            User question: "{user_query}"
            """

        print(prompt)
        response = model.generate_content(prompt)
        generated_sql = response.text.strip()

        if generated_sql.startswith("```sql"):
            generated_sql = generated_sql[len("```sql"):].strip()

        if generated_sql.endswith("```"):
            generated_sql = generated_sql[:-3].strip()

        # Safety check
        if not generated_sql.lower().startswith("select"):
            return jsonify({
                "error": "Sorry, I can only help with reading/querying data. Update or unrelated operations are not supported.",
                "generated_sql": generated_sql
            }), 400

        # Run SQL
        results = run_sql_query(generated_sql)
        print(generated_sql)

        html_table = results_to_html(results)
        print(html_table)
        return jsonify({
            "user_query": user_query,
            "html_result": html_table
        })
        # return jsonify({
        #     "user_query": user_query,
        #     "generated_sql": generated_sql,
        #     "results": results
        # })
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5500, debug=True)
    app.run(host='0.0.0.0', port=5500, debug=True)
