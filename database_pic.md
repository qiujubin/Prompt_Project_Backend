# 数据库ER图

## 实体

### users

- id (PK)
- username
- email
- hashed_password
- avatar_url
- is_active
- created_at
- updated_at
- full_name
- phone
- last_login_at
- source

### social_accounts

- id (PK)
- user_id (FK → users.id)
- openid
- access_token
- refresh_token
- expires_at
- created_at
- nickname
- unionid

### drawings

- id (PK)
- user_id (FK → users.id)
- prompt
- model_name
- image_url
- status
- created_at
- width
- height
- seed
- negative_prompt
- ai_response_time_ms
- is_public

### prompt_categories

- id (PK)
- name
- display_name
- sort_order

### prompt_subcategories

- id (PK)
- category_id (FK → prompt_categories.id)
- name
- display_name
- sort_order

### prompt_keywords

- id (PK)
- word
- small_category_id (FK → prompt_subcategories.id)
- created_by (FK → users.id)
- created_at

### prompt_logs

- id (PK)
- user_id (FK → users.id)
- used_at
- small_category_id (FK → prompt_subcategories.id)
- weight
- is_navigate
- drawing_id (FK → drawings.id)

### user_favorites

- user_id (FK → users.id)
- keyword_id (FK → prompt_keywords.id)
- favorited_at
- PK: (user_id, keyword_id)

### user_prompt_keywords

- user_id (FK → users.id)
- keyword_id (FK → prompt_keywords.id)
- used_count
- last_used_at
- PK: (user_id, keyword_id)
