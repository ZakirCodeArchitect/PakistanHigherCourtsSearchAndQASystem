# Manual migration to add enhanced metadata fields to existing SearchMetadata table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('search_indexing', '0003_increase_canonical_term_length'),
    ]

    operations = [
        migrations.RunSQL(
            """
            -- Add TIER 1 ENHANCEMENT: Rich metadata fields
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS legal_entities JSONB DEFAULT '[]'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS legal_concepts JSONB DEFAULT '[]'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS case_classification JSONB DEFAULT '{}'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS subject_matter JSONB DEFAULT '[]'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS parties_intelligence JSONB DEFAULT '{}'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS procedural_stage VARCHAR(50) DEFAULT '';
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS case_timeline JSONB DEFAULT '[]'::jsonb;
            
            -- Add TIER 1 ENHANCEMENT: Quality and relevance scores
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS content_richness_score FLOAT DEFAULT 0.0;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS data_completeness_score FLOAT DEFAULT 0.0;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS authority_score FLOAT DEFAULT 0.0;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS precedential_value FLOAT DEFAULT 0.0;
            
            -- Add TIER 1 ENHANCEMENT: Search optimization
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS searchable_keywords JSONB DEFAULT '[]'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS semantic_tags JSONB DEFAULT '[]'::jsonb;
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS relevance_boosters JSONB DEFAULT '[]'::jsonb;
            
            -- Add metadata tracking fields
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS enhanced_metadata_hash VARCHAR(64) DEFAULT '';
            ALTER TABLE search_metadata ADD COLUMN IF NOT EXISTS enhanced_metadata_extracted BOOLEAN DEFAULT FALSE;
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS search_meta_procedural_stage_idx ON search_metadata(procedural_stage);
            CREATE INDEX IF NOT EXISTS search_meta_content_richness_score_idx ON search_metadata(content_richness_score);
            CREATE INDEX IF NOT EXISTS search_meta_data_completeness_score_idx ON search_metadata(data_completeness_score);
            CREATE INDEX IF NOT EXISTS search_meta_authority_score_idx ON search_metadata(authority_score);
            CREATE INDEX IF NOT EXISTS search_meta_precedential_value_idx ON search_metadata(precedential_value);
            CREATE INDEX IF NOT EXISTS search_meta_enhanced_metadata_hash_idx ON search_metadata(enhanced_metadata_hash);
            CREATE INDEX IF NOT EXISTS search_meta_enhanced_metadata_extracted_idx ON search_metadata(enhanced_metadata_extracted);
            """,
            reverse_sql="""
            -- Remove indexes
            DROP INDEX IF EXISTS search_meta_procedural_stage_idx;
            DROP INDEX IF EXISTS search_meta_content_richness_score_idx;
            DROP INDEX IF EXISTS search_meta_data_completeness_score_idx;
            DROP INDEX IF EXISTS search_meta_authority_score_idx;
            DROP INDEX IF EXISTS search_meta_precedential_value_idx;
            DROP INDEX IF EXISTS search_meta_enhanced_metadata_hash_idx;
            DROP INDEX IF EXISTS search_meta_enhanced_metadata_extracted_idx;
            
            -- Remove columns
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS legal_entities;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS legal_concepts;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS case_classification;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS subject_matter;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS parties_intelligence;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS procedural_stage;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS case_timeline;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS content_richness_score;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS data_completeness_score;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS authority_score;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS precedential_value;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS searchable_keywords;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS semantic_tags;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS relevance_boosters;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS enhanced_metadata_hash;
            ALTER TABLE search_metadata DROP COLUMN IF EXISTS enhanced_metadata_extracted;
            """
        ),
    ]
