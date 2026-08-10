import { readonly, shallowRef } from "vue";

import { documentUploadsApi } from "../api/documentUploads";

export function useDocumentUpload() {
  const uploading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const uploadedFilename = shallowRef<string | null>(null);

  async function upload(file: File): Promise<boolean> {
    if (uploading.value) return false;

    uploading.value = true;
    error.value = null;
    uploadedFilename.value = null;
    try {
      const result = await documentUploadsApi.upload(file);
      uploadedFilename.value = result.asset.original_filename;
      return true;
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "PDF 上传失败";
      return false;
    } finally {
      uploading.value = false;
    }
  }

  return {
    uploading: readonly(uploading),
    error: readonly(error),
    uploadedFilename: readonly(uploadedFilename),
    upload,
  };
}
