from django.db import migrations


def create_cpu_node(apps, schema_editor):
    Node = apps.get_model('proxy', 'node')
    # Use update_or_create to be idempotent if migration is re-applied in tests
    Node.objects.update_or_create(
        name='CPU',
        defaults={
            'address': 'ollama',
            'port': 11434,
            'active': True,
            'available_models': [],
        }
    )


def remove_cpu_node(apps, schema_editor):
    Node = apps.get_model('proxy', 'node')
    Node.objects.filter(name='CPU', address='ollama', port=11434).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('proxy', '0008_ollama_cpu_node_add'),
    ]

    operations = [
        migrations.RunPython(create_cpu_node, remove_cpu_node),
    ]
