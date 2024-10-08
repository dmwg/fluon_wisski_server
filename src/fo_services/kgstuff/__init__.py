import logging
from collections.abc import Sequence
from typing import List

from ..db import (
    UpdateModelResult,
    export_interaction_data,
    export_user_data,
    get_itemlist_from_cluster,
    get_itemlist_from_model,
    is_new_user,
    update_model_infos,
)


logger = logging.getLogger(__name__)


class KGHandler(object):
    NUM_DEFAULT_RECOMMENDATIONS = 10

    def __init__(self):
        # we want to mimic the self.args-Object here without calling parse_self...
        # https://stackoverflow.com/a/2827734
        self.data_dir = "/app/"
        self.data_name = "data"

    def fill_sample_users(self):
        # for testing purposes: fill db with random user info
        import os

        from ..db import Base, db_session, engine
        from ..models import (
            InteractionHistory,
            ItemClusterInfo,
            RecommUser,
            UserRecommendationModel,
        )

        try:
            UserRecommendationModel.__table__.drop(engine)
            InteractionHistory.__table__.drop(engine)
            RecommUser.__table__.drop(engine)
            ItemClusterInfo.__table__.drop(engine)
        except Exception:
            pass
        Base.metadata.create_all(bind=engine)

        N = 3
        recomm_file = f"{self.data_dir}/{self.data_name}/recommendations.csv"
        if os.path.exists(recomm_file):
            with open(recomm_file, "rb") as f:
                try:  # catch OSError in case of a one line file
                    f.seek(-2, os.SEEK_END)
                    while f.read(1) != b"\n":
                        f.seek(-2, os.SEEK_CUR)
                except OSError:
                    f.seek(0)
                last_line = f.readline().decode()
                N = int(last_line.split(" ")[0]) + 1
        logger.warning(
            f"remember: I am creating {N} dummy users right now in KGHandler.fill_sample_data!"
        )

        for user_id in range(N):
            db_session.add(RecommUser(wisski_id=user_id))
        db_session.commit()
        return N

    def fill_sample_interactions(self, n_users, n_interact_min, n_interact_max):
        # for testing purposes: fill db with random user info
        import random

        from ..db import db_session
        from ..models import InteractionHistory

        items = []
        with open(f"{self.data_dir}/{self.data_name}/items_id.txt", "r") as f:
            field = f.readline().strip().split(" ")[2]
            if field != "wisskiid":
                raise Exception("Deep Shit Error Code")
            for line in f:
                items.append(int(line.strip().split(" ")[2]))

        for user in range(n_users):
            n = random.choice(range(n_interact_min, n_interact_max + 1))
            interactions = random.sample(items, k=n)
            for item in interactions:
                db_session.add(InteractionHistory(wisski_user=user, wisski_item=item))

        db_session.commit()

    def load_sampled_data(self):
        # import recommendable items to database
        # ~ self.N = self.fill_sample_users()

        # ~ n_interact_min = 10
        # ~ n_interact_max = 50
        # ~ self.fill_sample_interactions(self.N,n_interact_min,n_interact_max)
        pass

    def reload_data(
        self, cluster_data: Sequence, reco_data: Sequence
    ) -> UpdateModelResult:
        return update_model_infos(cluster_data, reco_data)

    def export_user_data(self):
        usr_file = "/app/known_users.tsv"
        export_user_data(usr_file)
        return usr_file

    def export_interaction_data(self):
        intr_file = "/app/user_interactions.tsv"
        export_interaction_data(intr_file)
        return intr_file

    def recommend_me_something(
        self, user_id: int, max_n: int, offset: int
    ) -> List[int]:
        if offset > 0:
            max_n += offset

        if is_new_user(user_id):
            reco_items = get_itemlist_from_cluster(self.NUM_DEFAULT_RECOMMENDATIONS)
            logger.debug(f"new user. get itemlist from cluster: {reco_items}")
        else:
            reco_items = get_itemlist_from_model(user_id, max_n)
            if len(reco_items) == 0:
                reco_items = get_itemlist_from_cluster(self.NUM_DEFAULT_RECOMMENDATIONS)
                logger.debug(
                    f"known user. no recommendations. get itemlist from cluster: {reco_items}"
                )
            else:
                logger.debug(f"known user. get itemlist from model: {reco_items}")

        if offset > 0:
            reco_items = reco_items[offset : len(reco_items)]

        logger.debug(f"recommending something for wisski user {user_id}")

        return [r[0] for r in reco_items]
