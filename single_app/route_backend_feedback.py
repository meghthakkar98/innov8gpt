# route_backend_feedback.py

from config import *
from functions_authentication import *
from functions_settings import *   

def register_route_backend_feedback(app):

    @app.route("/feedback/submit", methods=["POST"])
    @login_required
    @user_required
    @enabled_required("enable_user_feedback")
    def feedback_submit():
        """
        Endpoint to store user feedback:
          POST /feedback/submit
          JSON body: { messageId, conversationId, feedbackType, reason }
        """
        data = request.get_json()
        messageId = data.get("messageId")
        conversationId = data.get("conversationId")
        feedbackType = data.get("feedbackType")
        reason = data.get("reason", "")
        user_id = None
        if "user" in session:
            user_id = session["user"].get("oid") or session["user"].get("sub")

        if not messageId or not conversationId or not feedbackType:
            return jsonify({"error": "Missing required fields"}), 400

        try:
            conversation_doc = container.read_item(
                item=conversationId, partition_key=conversationId
            )
        except:
            return jsonify({"error": "Conversation not found"}), 404

        ai_message_text = None
        user_prompt_text = None

        all_messages = conversation_doc.get("messages", [])
        for msg in all_messages:
            if msg["role"] == "assistant" and msg.get("message_id") == messageId:
                ai_message_text = msg["content"]
        reversed_messages = list(reversed(all_messages))
        for msg in reversed_messages:
            if msg["role"] == "user":
                user_prompt_text = msg["content"]
                break

        if not ai_message_text:
            ai_message_text = "[AI response text not found]"

        if not user_prompt_text:
            user_prompt_text = "[User prompt not found]"

        feedback_id = str(uuid.uuid4())
        item = {
            "id": feedback_id,
            "userId": user_id,
            "prompt": user_prompt_text,
            "aiResponse": ai_message_text,
            "feedbackType": feedbackType,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "adminReview": {
                "acknowledged": False,
                "analyzedBy": None,
                "analysisNotes": None,
                "responseToUser": None,
                "actionTaken": None,
                "reviewTimestamp": None
            }
        }

        feedback_container.upsert_item(item)

        return jsonify({"success": True, "feedbackId": feedback_id})
    

    @app.route("/feedback/review", methods=["GET"])
    @login_required
    @admin_required
    @enabled_required("enable_user_feedback")
    def feedback_review_get():
        """
        Return all feedback for admin. For real-world scenarios,
        you'd likely paginate or filter by date, etc.
        """
        query = "SELECT * FROM c"
        items = list(feedback_container.query_items(query=query, enable_cross_partition_query=True))

        results = []
        for f in items:
            results.append({
                "id": f["id"],
                "userId": f.get("userId"),
                "prompt": f.get("prompt"),
                "aiResponse": f.get("aiResponse"),
                "feedbackType": f.get("feedbackType"),
                "reason": f.get("reason"),
                "timestamp": f.get("timestamp"),
                "adminReview": f.get("adminReview", {})
            })
        return jsonify(results)


    @app.route("/feedback/review/<feedbackId>", methods=["PATCH"])
    @login_required
    @admin_required
    @enabled_required("enable_user_feedback")
    def feedback_review_update(feedbackId):
        """
        Patch admin fields: acknowledged, analysisNotes, responseToUser, actionTaken
        """
        data = request.get_json()

        try:
            feedback_doc = feedback_container.read_item(
                item=feedbackId, partition_key=feedbackId
            )
        except:
            return jsonify({"error": "Feedback not found"}), 404

        adminReview = feedback_doc.get("adminReview", {})
        adminReview["acknowledged"] = data.get("acknowledged", adminReview.get("acknowledged", False))
        adminReview["analysisNotes"] = data.get("analysisNotes", adminReview.get("analysisNotes"))
        adminReview["responseToUser"] = data.get("responseToUser", adminReview.get("responseToUser"))
        adminReview["actionTaken"] = data.get("actionTaken", adminReview.get("actionTaken"))
        adminReview["reviewTimestamp"] = datetime.utcnow().isoformat()

        feedback_doc["adminReview"] = adminReview
        feedback_container.upsert_item(feedback_doc)

        return jsonify({"success": True})


    @app.route("/feedback/retest/<feedbackId>", methods=["POST"])
    @login_required
    @admin_required
    @enabled_required("enable_user_feedback")
    def feedback_retest(feedbackId):
        """
        Admin retests the prompt. We basically re-run the prompt
        against the current AI chain to see if it's improved.
        """
        data = request.get_json()
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Missing prompt"}), 400
        
        try:
            retestResponse = run_prompt_against_gpt(prompt)
            return jsonify({"retestResponse": retestResponse})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
    @app.route("/feedback/my", methods=["GET"])
    @login_required
    @user_required
    @enabled_required("enable_user_feedback")
    def feedback_my():
        """
        Returns ONLY the feedback items belonging to the current user in read-only format.
        """
        user_id = None
        if "user" in session:
            user_id = session["user"].get("oid") or session["user"].get("sub")
        if not user_id:
            return jsonify({"error": "No user ID found in session"}), 403

        query = f"SELECT * FROM c WHERE c.userId = '{user_id}'"
        items = list(feedback_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        results = []
        for f in items:
            results.append({
                "id": f["id"],
                "userId": f.get("userId"),
                "prompt": f.get("prompt"),
                "aiResponse": f.get("aiResponse"),
                "feedbackType": f.get("feedbackType"),
                "reason": f.get("reason"),
                "timestamp": f.get("timestamp"),
                "adminReview": f.get("adminReview", {})
            })
        return jsonify(results)


def run_prompt_against_gpt(prompt):
    # To do -  Replace with the real logic of your chat pipeline
    return f"[Retested with new model] AI response for: {prompt}"