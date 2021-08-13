from falcon.status_codes import HTTP_200, HTTP_400
from sqlalchemy.orm import sessionmaker
import json,falcon

from api import logger, session, limiter, verify_token
from api.models import UserRatedRoute, Route, Comment

class RouteClass():
    @limiter.limit()
    def on_post(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.media

            route_id = int(data["route_id"])
            rating = int(data["rating"])

            routeRating = UserRatedRoute()
            routeRating.rating = rating
            routeRating.user_id = auth["user_id"]
            routeRating.route_id = route_id

            s = session()

            dbRouteRating = s.query(UserRatedRoute).filter(
                UserRatedRoute.user_id == auth["user_id"]).filter(UserRatedRoute.route_id == route_id).first()

            route = s.query(Route).filter(Route.id == route_id).first()

            if dbRouteRating is not None:
                if dbRouteRating.rating == 1:
                    route.one_star -= 1
                if dbRouteRating.rating == 2:
                    route.two_star -= 1
                if dbRouteRating.rating == 3:
                    route.three_star -= 1
                if dbRouteRating.rating == 4:
                    route.four_star -= 1
                if dbRouteRating.rating == 5:
                    route.five_star -= 1
                dbRouteRating.rating = rating

            if rating == 1:
                route.one_star += 1
            if rating == 2:
                route.two_star += 1
            if rating == 3:
                route.three_star += 1
            if rating == 4:
                route.four_star += 1
            if rating == 5:
                route.five_star += 1

            newRating = (route.one_star + route.two_star * 2 + route.three_star * 3 + route.four_star * 4 + route.five_star *
                      5) / (route.one_star + route.two_star + route.three_star + route.four_star + route.five_star)
            route.rating = newRating

            if dbRouteRating is None:
                s.add(routeRating)
            s.commit()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps({"rating": newRating})
        except(Exception) as e:
            logger.error("Route post: " + str(e))
            resp.body = 'Failed'
            resp.status = falcon.HTTP_400

    @limiter.limit()
    def on_get(self, req, resp):
        try:
            auth = verify_token(req.auth)

            data = req.params
            route_id = int(data["route_id"])
            comment_count = 0

            s = session()

            
            dbRouteRating = s.query(UserRatedRoute).filter(
                UserRatedRoute.user_id == auth["user_id"]).filter(UserRatedRoute.route_id == route_id).first()

            route = s.query(Route).filter(Route.id == route_id).first()
            ratingCount = route.one_star + route.two_star + route.three_star + route.four_star + route.five_star
            comment_count = s.query(Comment).filter(Comment.route_id == route_id).count()
            s.close()

            resp.status = falcon.HTTP_200
            resp.body = json.dumps(
                {"route": route.name, "rating": route.rating, "rating_count": ratingCount, "commentCount": comment_count, "user_rating": dbRouteRating.rating if dbRouteRating is not None else 0})
        except(Exception) as e:
            resp.status = falcon.HTTP_400
            resp.body = 'Failed'
            logger.error('Route get: ' + str(e))