import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def fix_trigger():
    print("Attempting to fix database triggers...")
    
    # SQL to check if trigger exists and drop it if it references non-existent column
    # Or just try to drop the trigger for user_favorites if it exists
    
    # The error message suggests: PL/pgSQL assignment "NEW.updated_at = NOW()"
    # This usually comes from a generic trigger function applied to the table
    # But UserFavorite model doesn't have updated_at column.
    
    # Let's inspect triggers on user_favorites
    
    with engine.connect() as conn:
        # Check if table has updated_at column
        try:
            conn.execute(text("SELECT updated_at FROM user_favorites LIMIT 1"))
            print("user_favorites has updated_at column.")
            has_column = True
        except Exception:
            print("user_favorites does NOT have updated_at column.")
            has_column = False
            
        if not has_column:
            # If it doesn't have the column, we must remove the trigger that tries to update it
            # Common name for such trigger is update_user_favorites_modtime or similar
            # Or we can check pg_trigger
            
            # Drop trigger if exists
            try:
                # Assuming the trigger name follows convention or just dropping the one causing issues
                # Often named 'update_user_favorites_changetimestamp' or similar
                
                # Let's find triggers on this table
                result = conn.execute(text("""
                    SELECT trigger_name 
                    FROM information_schema.triggers 
                    WHERE event_object_table = 'user_favorites'
                """))
                
                triggers = result.fetchall()
                print(f"Found triggers: {triggers}")
                
                for row in triggers:
                    trigger_name = row[0]
                    # We can't easily know which one is the culprit without logic, 
                    # but if there is one calling update_updated_at_column(), we should drop it.
                    
                    # Safer approach: Add the updated_at column to the model and DB
                    # This is better for consistency anyway.
                    pass
            except Exception as e:
                print(f"Error checking triggers: {e}")

        # Alternative fix: Add updated_at column to user_favorites table
        if not has_column:
            print("Adding updated_at column to user_favorites...")
            conn.execute(text("ALTER TABLE user_favorites ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
            print("Added updated_at column.")
            conn.commit()
        
        print("Fix complete.")

if __name__ == "__main__":
    fix_trigger()
