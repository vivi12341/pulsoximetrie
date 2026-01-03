# ==============================================================================
# auth/models.py
# ------------------------------------------------------------------------------
# ROL: Modele SQLAlchemy pentru autentificare medici:
#      - Doctor (utilizatori medici)
#      - PasswordResetToken (token-uri reset parolă)
#      - LoginSession (tracking sesiuni active)
#
# RESPECTĂ: .cursorrules - Zero date personale în log-uri, GDPR compliant
# ==============================================================================

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from typing import Optional

db = SQLAlchemy()


# ==============================================================================
# MODEL: Doctor (Utilizatori Medici)
# ==============================================================================

class Doctor(UserMixin, db.Model):
    """
    Model pentru utilizatori medici cu autentificare.
    
    ⚠️ GDPR: NU stocăm date personale sensibile (CNP, adresă, telefon personal)
    """
    __tablename__ = 'doctors'
    
    # Identificare
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    
    # Status cont
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(50))
    
    # Rate limiting (protecție brute-force)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    
    # Relații
    reset_tokens = db.relationship('PasswordResetToken', back_populates='doctor', 
                                   cascade='all, delete-orphan', lazy='dynamic')
    sessions = db.relationship('LoginSession', back_populates='doctor', 
                              cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f"<Doctor {self.email} (ID: {self.id})>"
    
    def get_id(self):
        """Necesar pentru Flask-Login."""
        return str(self.id)
    
    def is_locked(self) -> bool:
        """Verifică dacă contul este blocat temporar (brute-force protection)."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self, minutes: int = 15):
        """Blochează contul pentru X minute după încercări eșuate."""
        self.locked_until = datetime.utcnow() + timedelta(minutes=minutes)
        self.failed_login_attempts += 1
        db.session.commit()
    
    def unlock_account(self):
        """Deblochează contul și resetează încercările eșuate."""
        self.locked_until = None
        self.failed_login_attempts = 0
        db.session.commit()
    
    def record_successful_login(self, ip_address: str):
        """Înregistrează un login reușit."""
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()
    
    def to_dict(self) -> dict:
        """Returnează un dicționar cu date publice (fără parolă!)."""
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'last_login_ip': self.last_login_ip
        }


# ==============================================================================
# MODEL: PasswordResetToken (Token-uri Reset Parolă)
# ==============================================================================

class PasswordResetToken(db.Model):
    """
    Token-uri pentru resetare parolă prin email.
    
    SECURITATE:
    - Token-uri unice, securizate (itsdangerous)
    - Expiră după 1h
    - Folosire unică (used_at != NULL după utilizare)
    """
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime)
    
    # Tracking
    ip_address = db.Column(db.String(50))
    
    # Relații
    doctor = db.relationship('Doctor', back_populates='reset_tokens')
    
    def __repr__(self):
        return f"<PasswordResetToken {self.token[:10]}... for Doctor ID {self.doctor_id}>"
    
    def is_valid(self) -> bool:
        """
        Verifică dacă token-ul este valid:
        - Nu a fost folosit (used_at == NULL)
        - Nu a expirat (expires_at > acum)
        """
        if self.used_at is not None:
            return False
        return datetime.utcnow() < self.expires_at
    
    def mark_as_used(self):
        """Marchează token-ul ca folosit (protecție refolosire)."""
        self.used_at = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def cleanup_expired_tokens():
        """Șterge token-urile expirate (rulat periodic)."""
        expired_tokens = PasswordResetToken.query.filter(
            PasswordResetToken.expires_at < datetime.utcnow()
        ).all()
        
        for token in expired_tokens:
            db.session.delete(token)
        
        db.session.commit()
        return len(expired_tokens)


# ==============================================================================
# MODEL: LoginSession (Tracking Sesiuni Active)
# ==============================================================================

class LoginSession(db.Model):
    """
    Tracking sesiuni active pentru securitate și audit.
    
    FEATURES:
    - Istoricul login-urilor (ultimele 30 zile)
    - Posibilitate logout toate dispozitivele
    - Detectare login-uri suspecte (IP nou)
    """
    __tablename__ = 'login_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    
    # Tracking
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Relații
    doctor = db.relationship('Doctor', back_populates='sessions')
    
    def __repr__(self):
        return f"<LoginSession {self.session_token[:10]}... for Doctor ID {self.doctor_id}>"
    
    def update_activity(self):
        """Actualizează last_activity_at (pentru detectare inactivitate)."""
        self.last_activity_at = datetime.utcnow()
        db.session.commit()
    
    def deactivate(self):
        """Deactivează sesiunea (logout)."""
        self.is_active = False
        db.session.commit()
    
    @staticmethod
    def cleanup_old_sessions(days: int = 30):
        """Șterge sesiunile inactive mai vechi de X zile."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_sessions = LoginSession.query.filter(
            LoginSession.last_activity_at < cutoff_date,
            LoginSession.is_active == False
        ).all()
        
        for session in old_sessions:
            db.session.delete(session)
        
        db.session.commit()
        return len(old_sessions)
    
    @staticmethod
    def get_active_sessions_for_doctor(doctor_id: int, limit: int = 10):
        """Preia ultimele sesiuni active pentru un doctor."""
        return LoginSession.query.filter_by(
            doctor_id=doctor_id,
            is_active=True
        ).order_by(LoginSession.last_activity_at.desc()).limit(limit).all()
    
    @staticmethod
    def deactivate_all_for_doctor(doctor_id: int):
        """Deactivează toate sesiunile pentru un doctor (logout global)."""
        sessions = LoginSession.query.filter_by(
            doctor_id=doctor_id,
            is_active=True
        ).all()
        
        for session in sessions:
            session.is_active = False
        
        db.session.commit()
        return len(sessions)


# ==============================================================================
# MODEL: PatientRecording (Înregistrări Pacienți - PERSISTENT STORAGE)
# ==============================================================================

class PatientRecording(db.Model):
    """
    Înregistrări pulsoximetrie pentru pacienți.
    
    CRITICAL: Stored in PostgreSQL (PERSISTENT) instead of local JSON (EPHEMERAL).
    This ensures recordings survive Railway container restarts.
    
    RELAȚIE: One token (patient_link) → Many recordings
    """
    __tablename__ = 'patient_recordings'
    
    # Identificare
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), nullable=False, index=True)  # Patient link token
    recording_id = db.Column(db.String(8), nullable=False)  # Short ID for UI (e.g., "a3f1c2d4")
    
    # Fișier
    original_filename = db.Column(db.String(255), nullable=False)
    csv_path = db.Column(db.Text, nullable=False)  # Full path: local or "r2://bucket/key"
    r2_url = db.Column(db.Text)  # HTTP URL if stored in Scaleway R2
    storage_type = db.Column(db.String(10), default='local')  # 'local' or 'r2'
    
    # Metadata înregistrare
    recording_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Statistici SpO2
    avg_spo2 = db.Column(db.Numeric(5, 2))  # Ex: 97.50%
    min_spo2 = db.Column(db.Integer)  # Ex: 85
    max_spo2 = db.Column(db.Integer)  # Ex: 100
    
    # Tracking
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('doctors.id'))  # Optional: which doctor uploaded
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('token', 'recording_id', name='unique_token_recording'),
        db.Index('idx_recordings_token_date', 'token', 'recording_date'),
    )
    
    def __repr__(self):
        return f"<PatientRecording {self.recording_id} for token {self.token[:8]}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary (compatible with existing JSON format)."""
        return {
            'id': self.recording_id,  # Keep 'id' for backward compatibility
            'original_filename': self.original_filename,
            'csv_path': self.csv_path,
            'r2_url': self.r2_url,
            'storage_type': self.storage_type,
            'recording_date': self.recording_date.isoformat() if self.recording_date else None,
            'start_time': self.start_time.strftime('%H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M:%S') if self.end_time else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'stats': {
                'avg_spo2': float(self.avg_spo2) if self.avg_spo2 else None,
                'min_spo2': self.min_spo2,
                'max_spo2': self.max_spo2
            }
        }
    
    @staticmethod
    def create_from_dict(token: str, recording_dict: dict, created_by: int = None):
        """
        Create PatientRecording from dictionary (for migration from JSON).
        
        Args:
            token: Patient link token
            recording_dict: Recording metadata dictionary
            created_by: Optional doctor ID
            
        Returns:
            PatientRecording: Created instance
        """
        from dateutil.parser import parse as parse_date
        
        recording = PatientRecording(
            token=token,
            recording_id=recording_dict.get('id', str(uuid.uuid4())[:8]),
            original_filename=recording_dict.get('original_filename', 'unknown.csv'),
            csv_path=recording_dict.get('csv_path', ''),
            r2_url=recording_dict.get('r2_url'),
            storage_type=recording_dict.get('storage_type', 'local'),
            recording_date=parse_date(recording_dict['recording_date']).date() if 'recording_date' in recording_dict else None,
            start_time=parse_date(recording_dict['start_time']).time() if 'start_time' in recording_dict else None,
            end_time=parse_date(recording_dict['end_time']).time() if 'end_time' in recording_dict else None,
            avg_spo2=recording_dict.get('stats', {}).get('avg_spo2'),
            min_spo2=recording_dict.get('stats', {}).get('min_spo2'),
            max_spo2=recording_dict.get('stats', {}).get('max_spo2'),
            uploaded_at=parse_date(recording_dict['uploaded_at']) if 'uploaded_at' in recording_dict else datetime.utcnow(),
            created_by=created_by
        )
        
        db.session.add(recording)
        db.session.commit()
        
        return recording


# ==============================================================================
# FUNCȚII UTILITARE
# ==============================================================================

def init_db(app):
    """
    Inițializează database-ul cu aplicația Flask.
    
    CRITICAL: Includes self-healing logic to fix orphaned PostgreSQL objects
    from failed table creation attempts (e.g., sequence exists but table doesn't).
    
    Args:
        app: Instanța Flask/Dash
    """
    from logger_setup import logger
    
    # Folosim app.server pentru că Dash wraps Flask
    flask_app = app.server if hasattr(app, 'server') else app
    db.init_app(flask_app)
    
    with flask_app.app_context():
        # === SELF-HEALING: Auto-fix orphaned PostgreSQL objects ===
        try:
            logger.warning("🔧 [DB_INIT] Starting self-healing database check...")
            
            # Import psycopg2 for raw SQL execution
            import psycopg2
            from sqlalchemy import text
            
            # Check if patient_recordings table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'patient_recordings'
                );
            """)).scalar()
            
            table_exists = result
            
            if not table_exists:
                logger.warning("⚠️ [DB_INIT] patient_recordings table MISSING - checking for orphaned objects...")
                
                # Check for orphaned sequence
                seq_result = db.session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM pg_sequences 
                        WHERE schemaname = 'public' 
                        AND sequencename = 'patient_recordings_id_seq'
                    );
                """)).scalar()
                
                if seq_result:
                    logger.warning("🧹 [DB_INIT] Found orphaned sequence 'patient_recordings_id_seq' - cleaning up...")
                    
                    # Drop orphaned sequence
                    db.session.execute(text("DROP SEQUENCE IF EXISTS patient_recordings_id_seq CASCADE;"))
                    db.session.commit()
                    
                    logger.warning("✅ [DB_INIT] Orphaned sequence removed successfully")
                else:
                    logger.info("✅ [DB_INIT] No orphaned objects found")
            else:
                logger.info("✅ [DB_INIT] patient_recordings table already exists")
                
        except Exception as e:
            logger.warning(f"⚠️ [DB_INIT] Self-healing check failed (non-critical): {e}")
            # Non-critical - continue with normal initialization
        
        # === Create all tables ===
        logger.info("📊 [DB_INIT] Creating database tables...")
        db.create_all()
        
        logger.info("✅ Database inițializat: tabele create/verificate.")


def create_admin_user(email: str, password: str, full_name: str) -> Optional[Doctor]:
    """
    Creează primul utilizator admin (pentru setup inițial).
    
    Args:
        email: Email-ul adminului
        password: Parola (va fi hash-uită)
        full_name: Numele complet
        
    Returns:
        Doctor: Obiectul creat sau None dacă există deja
    """
    from auth.password_manager import hash_password
    from logger_setup import logger
    
    # Verificăm dacă există deja
    existing = Doctor.query.filter_by(email=email).first()
    if existing:
        logger.warning(f"⚠️ Utilizator cu email {email} există deja.")
        return None
    
    # Creăm adminul
    admin = Doctor(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        is_admin=True,
        is_active=True
    )
    
    db.session.add(admin)
    db.session.commit()
    
    logger.info(f"✅ Utilizator admin creat: {email}")
    return admin

