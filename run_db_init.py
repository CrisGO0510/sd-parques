#!/usr/bin/env python3
"""Execute database initialization script against Render PostgreSQL."""
import psycopg2
import sys

DATABASE_URL = "postgresql://sd_parques_db_user:25f9QZW4Vhyi1KGbD2Lhbgm8zp0zgOv1@dpg-d8eivvf40ujc73dl4110-a.ohio-postgres.render.com/sd_parques_db"

try:
    print("🔗 Conectando a Render PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Conexión exitosa")
    
    print("\n📝 Leyendo script SQL...")
    with open("server/init_db.sql", "r") as f:
        sql_script = f.read()
    
    print("⚙️  Ejecutando script...")
    cursor.execute(sql_script)
    conn.commit()
    print("✅ Script ejecutado correctamente")
    
    print("\n📊 Verificando creación de tabla...")
    cursor.execute("SELECT COUNT(*) FROM players;")
    result = cursor.fetchone()
    print(f"✅ Tabla 'players' creada exitosamente. Registros: {result[0]}")
    
    cursor.close()
    conn.close()
    print("\n🎉 ¡Base de datos inicializada correctamente en Render!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
