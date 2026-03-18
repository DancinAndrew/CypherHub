-- 確保 event-media  bucket 允許匿名讀取（部分 Supabase 版本需明確 policy）
CREATE POLICY "event_media_public_read"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'event-media');
