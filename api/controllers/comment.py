from falcon.status_codes import HTTP_200, HTTP_400
import datetime, json, falcon

from api import logger, session, client, limiter, verify_token
from api.models import Comment
class CommentClass:
    @limiter.limit()
    def on_get(self, req, resp):
        try:
            auth = verify_token(req.auth)
            data = req.params

            route_id = int(data["route_id"])
            page = int(data["page"])

            if page < 0 or route_id < 0 or route_id > 25:
                raise falcon.HTTPBadRequest(
                    title="Params out of range",
                    description="Invalid data, possible threat."
                )

            with client.connect() as con:
                comments = con.execute("SELECT c.id, c.text, c.user, c.route_id, c.rating, c.created_on, u.icon, u.id as user_id FROM public.comment c INNER JOIN public.user u ON u.name = c.user WHERE route_id = " +
                                       str(route_id) + " ORDER BY created_on DESC LIMIT 10 OFFSET " + str(page) + " * 10;")
                row_count = con.execute("Select COUNT(*) FROM public.comment WHERE route_id = " + str(route_id) + ";")

            comment_list = []
            comment_count = 0
            for row in row_count:
                comment_count = row["count"]

            for row in comments:
                comment_list.append(
                    {"id": row["id"], "icon": row["icon"], "user_id": row["user_id"], "text": row["text"], "user": row["user"], "route_id": row["route_id"]})

            resp.body = json.dumps(
                {"page": page, "comment_count": comment_count, "comments": comment_list})
            resp.status = falcon.HTTP_200
        except(Exception) as e:
            logger.error("Comment get: " + str(e))
            resp.body = 'Comment can not be retrieved.'
            resp.status = falcon.HTTP_400

    @limiter.limit()
    def on_post_rate(self, req, resp):
        try:
            auth = verify_token(req.auth)
            data = req.media
            resp.status = falcon.HTTP_200
        except(Exception) as e:
            resp.body = 'Comentariul nu a putut fi postat.'
            logger.error("Comment rate: " + str(e))
            resp.status = falcon.HTTP_400

    @limiter.limit()
    def on_post(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.media
            comment = Comment()
            comment.user_id = auth["user"]
            comment.text = data["text"]
            comment.route_id = int(data["route_id"])
            created_on = datetime.datetime.utcnow()
            comment.created_on = created_on

            s = session()
            s.add(comment)
            s.flush()

            id = comment.id
            s.commit()
            s.close()

            resp.body = json.dumps(
                {"id": id, "text": data["text"], "user": auth["user"], "user_id": auth["user_id"], "route_id": int(data["route_id"])})
            resp.status = falcon.HTTP_201

        except(Exception) as e:
            resp.body = 'Comentariul nu a putut fi postat.'
            logger.error("Comment post: " + str(e))
            resp.status = falcon.HTTP_400