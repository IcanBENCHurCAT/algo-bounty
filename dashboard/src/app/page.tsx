import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'

export default async function Page() {
  const cookieStore = await cookies()
  const supabase = createClient(cookieStore)

  const { data: todos } = await supabase.from('todos').select()

  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', background: '#0a0a0a', color: '#fff', minHeight: '100vh' }}>
      <h1>Supabase Todos List</h1>
      <ul>
        {todos?.map((todo) => (
          <li key={todo.id}>{todo.name}</li>
        ))}
      </ul>
    </div>
  )
}
