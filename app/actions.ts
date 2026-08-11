'use server'

import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'
import { createClient } from '@/lib/supabase/server'

async function uploadAvatarIfPresent(
  supabase: Awaited<ReturnType<typeof createClient>>,
  userId: string,
  formData: FormData
): Promise<string | null> {
  const file = formData.get('avatar')
  if (!(file instanceof File) || file.size === 0) return null

  const ext = file.name.split('.').pop() || 'jpg'
  const path = `${userId}/avatar-${Date.now()}.${ext}`

  const { error } = await supabase.storage.from('avatars').upload(path, file, {
    upsert: true,
    contentType: file.type,
  })
  if (error) throw new Error(`Avatar upload failed: ${error.message}`)

  const {
    data: { publicUrl },
  } = supabase.storage.from('avatars').getPublicUrl(path)
  return publicUrl
}

export async function createProfile(formData: FormData) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const avatarUrl = await uploadAvatarIfPresent(supabase, user.id, formData)

  const { error } = await supabase.from('profiles').insert({
    id: user.id,
    full_name: String(formData.get('full_name') ?? ''),
    headline: String(formData.get('headline') ?? '') || null,
    bio: String(formData.get('bio') ?? '') || null,
    location: String(formData.get('location') ?? '') || null,
    roles: formData.getAll('roles').map(String),
    avatar_url: avatarUrl,
  })
  if (error) throw new Error(error.message)

  redirect('/discover')
}

export async function updateProfile(formData: FormData) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const avatarUrl = await uploadAvatarIfPresent(supabase, user.id, formData)

  const update: Record<string, unknown> = {
    full_name: String(formData.get('full_name') ?? ''),
    headline: String(formData.get('headline') ?? '') || null,
    bio: String(formData.get('bio') ?? '') || null,
    location: String(formData.get('location') ?? '') || null,
    roles: formData.getAll('roles').map(String),
    updated_at: new Date().toISOString(),
  }
  if (avatarUrl) update.avatar_url = avatarUrl

  const { error } = await supabase.from('profiles').update(update).eq('id', user.id)
  if (error) throw new Error(error.message)

  revalidatePath(`/profile/${user.id}`)
  revalidatePath('/settings')
  redirect(`/profile/${user.id}`)
}

export async function addCredit(formData: FormData) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const yearRaw = String(formData.get('project_year') ?? '')

  const { error } = await supabase.from('credits').insert({
    profile_id: user.id,
    project_title: String(formData.get('project_title') ?? ''),
    role_on_project: String(formData.get('role_on_project') ?? ''),
    project_type: String(formData.get('project_type') ?? '') || null,
    project_year: yearRaw ? Number(yearRaw) : null,
  })
  if (error) throw new Error(error.message)

  revalidatePath('/settings')
  revalidatePath(`/profile/${user.id}`)
}

export async function deleteCredit(creditId: string) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { error } = await supabase
    .from('credits')
    .delete()
    .eq('id', creditId)
    .eq('profile_id', user.id)
  if (error) throw new Error(error.message)

  revalidatePath('/settings')
  revalidatePath(`/profile/${user.id}`)
}

export async function sendConnectionRequest(addresseeId: string) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { error } = await supabase.from('connections').insert({
    requester_id: user.id,
    addressee_id: addresseeId,
  })
  if (error) throw new Error(error.message)

  revalidatePath(`/profile/${addresseeId}`)
  revalidatePath('/connections')
}

export async function respondToConnection(connectionId: string, accept: boolean) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  if (accept) {
    const { error } = await supabase
      .from('connections')
      .update({ status: 'accepted' })
      .eq('id', connectionId)
    if (error) throw new Error(error.message)
  } else {
    const { error } = await supabase.from('connections').delete().eq('id', connectionId)
    if (error) throw new Error(error.message)
  }

  revalidatePath('/connections')
}

export async function removeConnection(connectionId: string) {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { error } = await supabase.from('connections').delete().eq('id', connectionId)
  if (error) throw new Error(error.message)

  revalidatePath('/connections')
}
