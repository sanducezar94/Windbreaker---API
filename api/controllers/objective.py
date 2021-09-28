from falcon.status_codes import HTTP_200, HTTP_400
from sqlalchemy.orm import sessionmaker
import json,falcon

from api import logger, session, limiter, verify_token
from api.models import Objective, UserRatedObjective, UserRatedRoute, Route, Comment

class ObjectiveClass():
    @limiter.limit()
    def on_post(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.media

            objective_id = int(data["objective_id"])
            rating = int(data["rating"])

            objectiveRating = UserRatedObjective()
            objectiveRating.rating = rating
            objectiveRating.user_id = auth["user_id"]
            objectiveRating.objective_id = objective_id

            s = session()

            dbObjectiveRating = s.query(UserRatedObjective).filter(
                UserRatedObjective.user_id == auth["user_id"]).filter(UserRatedObjective.objective_id == objective_id).first()

            objective = s.query(Objective).filter(Objective.id == objective_id).first()

            if dbObjectiveRating is not None:
                if dbObjectiveRating.rating == 1:
                    objective.one_star -= 1
                if dbObjectiveRating.rating == 2:
                    objective.two_star -= 1
                if dbObjectiveRating.rating == 3:
                    objective.three_star -= 1
                if dbObjectiveRating.rating == 4:
                    objective.four_star -= 1
                if dbObjectiveRating.rating == 5:
                    objective.five_star -= 1
                dbObjectiveRating.rating = rating

            if rating == 1:
                objective.one_star += 1
            if rating == 2:
                objective.two_star += 1
            if rating == 3:
                objective.three_star += 1
            if rating == 4:
                objective.four_star += 1
            if rating == 5:
                objective.five_star += 1

            newRating = (objective.one_star + objective.two_star * 2 + objective.three_star * 3 + objective.four_star * 4 + objective.five_star *
                      5) / (objective.one_star + objective.two_star + objective.three_star + objective.four_star + objective.five_star)
            objective.rating = newRating
            objective.rating_count = objective.one_star + objective.two_star + objective.three_star + objective.four_star + objective.five_star

            if dbObjectiveRating is None:
                s.add(objectiveRating)
            s.commit()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({"rating": newRating})
        except(Exception) as e:
            logger.error("Objective post: " + str(e))
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400

    @limiter.limit()
    def on_get(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.params
            objective_id = int(data["objective_id"])
            s = session()
            
            dbObjectiveRating = s.query(UserRatedObjective).filter(
                UserRatedObjective.user_id == auth["user_id"] and UserRatedObjective.objective_id == objective_id).filter(UserRatedObjective.objective_id == objective_id).first()

            objective = s.query(Objective).filter(Objective.id == objective_id).first()
            ratingCount = objective.rating_count
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps(
                {"objective": objective.name, "rating": objective.rating, "rating_count": ratingCount, "user_rating": dbObjectiveRating.rating if dbObjectiveRating is not None else 0})
        except(Exception) as e:
            resp.status = falcon.HTTP_400
            resp.body = 'Failed'
            logger.error('Objective get: ' + str(e))