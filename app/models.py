from sqlalchemy import (
    ForeignKey, create_engine, Column, Integer, String, Date, Time,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from faker import Faker
import random, datetime
from tqdm import tqdm
from app.database import DATABASE_URL, Base, get_db

#password = "kopigulaaren30"
#password = password.replace("@", "%40")
#DATABASE_URL = f"mysql+pymysql://root:{password}@localhost:3306/bioskop"

DATABASE_URL = f"mysql+pymysql://root:kopigulaaren30@localhost:3306/bioskop"
# DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Base = declarative_base()
fake = Faker("id_ID")

NUM_STUDIOS = 5
NUM_MEMBERS = 100
ORDERS_TO_GENERATE = 1000

MIN_ROWS = 8
MIN_COLS = 6


def gen(prefix, i, width):
    return f"{prefix}{str(i).zfill(width)}"




class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    title = Column(String(200))
    genre = Column(String(100))
    durasi = Column(Integer)
    director = Column(String(200))
    rating = Column(String(10))
    price = Column(Integer)


class Studio(Base):
    __tablename__ = "studios"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    name = Column(String(100))
    rows = Column(Integer)
    cols = Column(Integer)


class StudioSeat(Base):
    __tablename__ = "studio_seats"
    id = Column(Integer, primary_key=True)
    studio_id = Column(Integer)
    row = Column(String(3))
    col = Column(Integer)
    __table_args__ = (UniqueConstraint("studio_id", "row", "col"),)


class Membership(Base):
    __tablename__ = "memberships"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    nama = Column(String(255))


class Jadwal(Base):
    __tablename__ = "jadwal"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)

    movie_id = Column(Integer, ForeignKey("movies.id"))
    movie = relationship("Movie")
    movie_code = Column(String(20))

    studio_id = Column(Integer, ForeignKey("studios.id"))
    studio = relationship("Studio")
    studio_code = Column(String(20))
    
    tanggal = Column(Date)
    jam = Column(Time)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    membership_id = Column(Integer)
    membership_code = Column(String(20))
    jadwal_id = Column(Integer)
    payment_method = Column(String(50))
    seat_count = Column(Integer)
    promo_name = Column(String(100))
    discount = Column(Integer)
    total_price = Column(Integer)
    final_price = Column(Integer)
    cash = Column(Integer)
    change = Column(Integer)
    transaction_date = Column(Date)
    hari = Column(String(10))


class OrderSeat(Base):
    __tablename__ = "order_seats"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer)
    jadwal_id = Column(Integer)
    studio_id = Column(Integer)
    row = Column(String(3))
    col = Column(Integer)
    __table_args__ = (UniqueConstraint("jadwal_id", "row", "col"),)


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True)
    membership_id = Column(Integer)
    membership_code = Column(String(20))
    jadwal_id = Column(Integer)
    studio_id = Column(Integer)
    row = Column(String(3))
    col = Column(Integer)
    __table_args__ = (UniqueConstraint("membership_id", "jadwal_id", "row", "col"),)


def price(dur):
    if dur >= 180:
        return 50000
    if dur >= 125:
        return 45000
    return 40000


def seat_free(s, j, st, r, c):
    x = s.query(OrderSeat).filter_by(jadwal_id=j, studio_id=st, row=r, col=c).first()
    return x is None


engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)




def main():
    with engine.connect() as connection:
        with connection.begin() as transaction:
            try:
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
                print("INFO: Foreign Key Checks dimatikan sementara.")
            except Exception as e:
                print(f"PERINGATAN: Gagal mematikan FK Checks. {e}")
            
            Base.metadata.drop_all(connection)
            print("INFO: Metadata drop_all berhasil dieksekusi.")
            
            Base.metadata.create_all(connection)
            print("INFO: Metadata create_all berhasil dieksekusi.")

            try:
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
                print("INFO: Foreign Key Checks diaktifkan kembali.")
            except Exception as e:
                print(f"PERINGATAN: Gagal mengaktifkan FK Checks. {e}")
            
            transaction.commit()
    db = Session()

    FILMS = [
        ("Avengers: Endgame", "Action, Fantasy", 200, "Anthony Russo, Joe Russo", "PG-13"),
        ("The Conjuring", "Horror, Mystery", 120, "James Wan", "17+"),
        ("Frozen", "Family, Musical", 130, " Jennifer Lee, Chris Buck", "PG"),
        ("Komang", "Drama, Romance", 130, "Naya Anindita", "13+"),
        ("Detective Conan: One-eyed Flashback", "Anime, Mystery", 125, "Katsuya Shigehara", "13+")
    ]

    movies = []
    for i, (t, g, d, dirc, rate) in enumerate(FILMS, 1):
        m = Movie(
            code=gen("MOV", i, 3),
            title=t,
            genre=g,
            durasi=d,
            director=dirc,
            rating=rate,
            price=price(d)
        )
        db.add(m)
        movies.append(m)
    db.commit()



    studios = []
    for i in range(1, NUM_STUDIOS + 1):
        rows = random.randint(MIN_ROWS, MIN_ROWS + 5)
        cols = random.randint(MIN_COLS, MIN_COLS + 5)

        s = Studio(code=gen("ST", i, 3), name=f"Studio {i}", rows=rows, cols=cols)
        db.add(s)
        db.flush()

        rl = [chr(ord("A") + k) for k in range(rows)]
        for rr in rl:
            for cc in range(1, cols + 1):
                db.add(StudioSeat(studio_id=s.id, row=rr, col=cc))

        studios.append(s)

    db.commit()



    members = []
    for i in range(1, NUM_MEMBERS + 1):
        m = Membership(code=gen("MEM", i, 3), nama=fake.name())
        db.add(m)
        members.append(m)
    db.commit()



    jadw = []
    j = 1
    times = [datetime.time(11, 0), datetime.time(16, 0), datetime.time(20, 30)]

    for d in range(1, 32):
        dt = datetime.date(2024, 12, d)
        for mv in movies:
            for hm in times:
                st = random.choice(studios)
                jd = Jadwal(
                    code=gen("JAD", j, 4),
                    movie_id=mv.id,
                    movie_code=mv.code,
                    studio_id=st.id,
                    studio_code=st.code,
                    tanggal=dt,
                    jam=hm
                )
                db.add(jd)
                db.flush()
                jadw.append(jd)
                j += 1
    db.commit()



    methods = ["QRIS", "Debit", "Gopay", "ShopeePay", "CASH"]

    hari_map = {
        0: "Senin",
        1: "Selasa",
        2: "Rabu",
        3: "Kamis",
        4: "Jumat",
        5: "Sabtu",
        6: "Minggu"
    }

    done = 0
    tries = 0

    progress = tqdm(total=ORDERS_TO_GENERATE, desc="Building Orders", unit="order")

    while done < ORDERS_TO_GENERATE and tries < ORDERS_TO_GENERATE * 20:
        tries += 1

        jd = random.choice(jadw)
        mv = db.query(Movie).filter_by(id=jd.movie_id).first()
        st = db.query(Studio).filter_by(id=jd.studio_id).first()
        mem = random.choice(members)

        want = random.randint(1, 6)

        rl = [chr(ord('A') + k) for k in range(st.rows)]
        seats = []
        att = 0

        while len(seats) < want and att < 50:
            att += 1
            r = random.choice(rl)
            c = random.randint(1, st.cols)
            if (r, c) in seats:
                continue
            if seat_free(db, jd.id, st.id, r, c):
                seats.append((r, c))

        if not seats:
            continue

        promo = "NO PROMO"
        disc = 0

        if jd.tanggal.day == 12:
            promo = "SUPER 12.12"
            disc = 30
        elif len(seats) >= 5:
            promo = "BULK 5+"
            disc = 20

        tot = mv.price * len(seats)
        fin = tot - int(tot * disc / 100)

        pm = random.choice(methods)
        cash_val = None
        change_val = None

        if pm == "CASH":
            cash_val = random.choice([fin, fin + 5000, fin + 10000, fin + 20000])
            change_val = cash_val - fin

        o = Order(
            code=gen("ORD", done + 1, 6),
            membership_id=mem.id,
            membership_code=mem.code,
            jadwal_id=jd.id,
            payment_method=pm,
            seat_count=len(seats),
            promo_name=promo,
            discount=disc,
            total_price=tot,
            final_price=fin,
            cash=cash_val,
            change=change_val,
            transaction_date=jd.tanggal,
            hari=hari_map[jd.tanggal.weekday()]
        )
        db.add(o)
        db.flush()

        for (r, c) in seats:
            db.add(OrderSeat(order_id=o.id, jadwal_id=jd.id, studio_id=st.id, row=r, col=c))

        try:
            db.commit()
            done += 1
            progress.update(1)
        except:
            db.rollback()
            continue

    progress.close()
    print("\nDONE:", done, "orders")


if __name__ == "__main__":
    main()
