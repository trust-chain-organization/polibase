-- Add GCS URI columns to meetings table
ALTER TABLE meetings
ADD COLUMN gcs_pdf_uri VARCHAR(512),
ADD COLUMN gcs_text_uri VARCHAR(512);

-- Add indexes for GCS URI columns
CREATE INDEX idx_meetings_gcs_pdf_uri ON meetings(gcs_pdf_uri);
CREATE INDEX idx_meetings_gcs_text_uri ON meetings(gcs_text_uri);

-- Add comments for columns
COMMENT ON COLUMN meetings.gcs_pdf_uri IS 'Google Cloud Storage URI for the PDF file (gs://bucket-name/path/to/file.pdf)';
COMMENT ON COLUMN meetings.gcs_text_uri IS 'Google Cloud Storage URI for the extracted text file (gs://bucket-name/path/to/file.txt)';
