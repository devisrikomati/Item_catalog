from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Shoppingmall, Base, Cloth, User

engine = create_engine('sqlite:///dresses.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()
User1 = User(name="devisri", email="devisrikomati@gmail.com")
session.add(User1)
session.commit()


shoppingmall1 = Shoppingmall(user_id=1, name="Z_square")
session.add(shoppingmall1)
session.commit()
cloth1 = Cloth(user_id=1, name="Linen", description="ladies dresses",
                   price="$40", type="kurthees", shoppingmall=shoppingmall1)

session.add(cloth1)
session.commit()

cloth2 = Cloth(user_id=1, name="kachi pattu", description="womens ware",
                   type="saries", price="$90", shoppingmall=shoppingmall1)

session.add(cloth2)
session.commit()

cloth3 = Cloth(user_id=1, name="jeans",
                   description="both men and women can use",
                   type="pants", price="$40", shoppingmall=shoppingmall1)

session.add(cloth3)
session.commit()

shoppingmall2 = Shoppingmall(user_id=1, name="select city walk")
session.add(shoppingmall2)
session.commit()

cloth1 = Cloth(user_id=1, name="cotton",
                   description="its comfortable to wear in summer ",
                   price="$25", type="night dresses", shoppingmall=shoppingmall2)

session.add(cloth1)
session.commit()

cloth2 = Cloth(user_id=1, name="Silk",
                   description="Silk cloths always looks good ",
                   price="$60", type="chudidhars", shoppingmall=shoppingmall2)

session.add(cloth2)
session.commit()

cloth3 = Cloth(user_id=1, name="cotton and silk mixer",
                   description="functionary ware long kalis,saries...",
                   price="$65", type="long dresses", shoppingmall=shoppingmall2)

session.add(cloth3)
session.commit()

shoppingmall3 = Shoppingmall(user_id=1, name="Fun republic")
session.add(shoppingmall3)
session.commit()

cloth1 = Cloth(user_id=1, name="kids",
                   description=" Kids shopping zone ",
                   price="$60", type="T-shirts",  shoppingmall=shoppingmall3)

session.add(cloth1)
session.commit()

cloth2 = Cloth(user_id=1, name="summer cravings",
                   description="it's fully made by pure cotton",
                   price="$90", type="blue color", shoppingmall=shoppingmall3)

session.add(cloth2)
session.commit()

cloth3 = Cloth(user_id=1, name="winter cavings ",
                   description="this is totally  made by wool ",
                   price="$40", type="sweters",  shoppingmall=shoppingmall3)

session.add(cloth3)
session.commit()

print("Cloth details are added!")
