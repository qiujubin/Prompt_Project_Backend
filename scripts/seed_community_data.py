import sys
import os
import random
from datetime import datetime, timedelta

# 添加项目根目录到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings
from core.security import get_password_hash
from models.user import User
from models.drawing import Drawing
from models.drawing_interaction import DrawingLike, DrawingFavorite, DrawingComment
from models.user_favorite import UserFavorite # 旧的收藏表，如果不兼容可以不管，但这里我们用新的 DrawingFavorite

# 初始化数据库连接
engine = create_engine(settings.DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    db = SessionLocal()
    try:
        # 1. 创建测试用户
        print("Creating users...")
        users = []
        for i in range(1, 11):
            username = f"user{i}"
            email = f"user{i}@example.com"
            existing_user = db.query(User).filter(User.username == username).first()
            if not existing_user:
                new_user = User(
                    username=username,
                    email=email,
                    hashed_password=get_password_hash("123456"),
                    is_active=True,
                    avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
                )
                db.add(new_user)
                users.append(new_user)
            else:
                users.append(existing_user)
        db.commit()
        
        # 重新获取用户以获得 ID
        users = db.query(User).filter(User.username.in_([f"user{i}" for i in range(1, 11)])).all()
        print(f"Created/Found {len(users)} users.")

        # 2. 创建测试画作
        print("Creating drawings...")
        prompts = [
            "A futuristic city at sunset, cyberpunk style",
            "A cute cat playing with a ball of yarn, watercolor",
            "A majestic dragon flying over a mountain range, fantasy art",
            "Portrait of a warrior princess, detailed armor, digital painting",
            "A serene lake in a forest, misty morning, photorealistic",
            "Space station orbiting a blue planet, sci-fi",
            "Steampunk robot drinking coffee, intricate details",
            "Abstract composition of geometric shapes, vibrant colors",
            "Traditional Japanese garden with cherry blossoms, oil painting",
            "A post-apocalyptic wasteland with a lone survivor, cinematic lighting"
        ]
        
        drawings = []
        for i in range(20):
            user = random.choice(users)
            prompt = random.choice(prompts)
            drawing = Drawing(
                user_id=user.id,
                prompt=prompt,
                model_name="stable-diffusion-xl",
                image_url=f"https://picsum.photos/seed/{i}/512/512", # 使用随机图片占位
                status="completed",
                width=512,
                height=512,
                is_public=True,
                view_count=random.randint(10, 1000)
            )
            db.add(drawing)
            drawings.append(drawing)
        db.commit()
        
        # 重新获取画作以获得 ID
        # 注意：这里为了简单，假设刚刚插入的就是最新的20个，或者直接查所有is_public=True的
        drawings = db.query(Drawing).filter(Drawing.is_public == True).order_by(Drawing.id.desc()).limit(20).all()
        print(f"Created/Found {len(drawings)} drawings.")

        # 3. 生成互动数据
        print("Generating interactions...")
        for drawing in drawings:
            # 点赞
            like_count = 0
            for user in users:
                if random.random() < 0.3: # 30% 概率点赞
                    existing_like = db.query(DrawingLike).filter(
                        DrawingLike.user_id == user.id, 
                        DrawingLike.drawing_id == drawing.id
                    ).first()
                    if not existing_like:
                        like = DrawingLike(user_id=user.id, drawing_id=drawing.id)
                        db.add(like)
                        like_count += 1
            
            # 收藏
            favorite_count = 0
            for user in users:
                if random.random() < 0.1: # 10% 概率收藏
                    existing_fav = db.query(DrawingFavorite).filter(
                        DrawingFavorite.user_id == user.id, 
                        DrawingFavorite.drawing_id == drawing.id
                    ).first()
                    if not existing_fav:
                        fav = DrawingFavorite(user_id=user.id, drawing_id=drawing.id)
                        db.add(fav)
                        favorite_count += 1
            
            # 评论
            comment_count = 0
            comments_texts = [
                "Awesome!", "Great work!", "Love the colors.", "How did you do that?", 
                "Nice prompt.", "Can you share the seed?", "Looks amazing.", "Wow!",
                "Not bad.", "Interesting style."
            ]
            for _ in range(random.randint(0, 5)): # 每张图 0-5 条评论
                user = random.choice(users)
                comment = DrawingComment(
                    user_id=user.id,
                    drawing_id=drawing.id,
                    content=random.choice(comments_texts)
                )
                db.add(comment)
                comment_count += 1
            
            # 更新统计数据 (增量更新，因为刚刚插入了)
            drawing.like_count += like_count
            drawing.favorite_count += favorite_count
            drawing.comment_count += comment_count
            
        db.commit()
        print("Data seeding completed successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
