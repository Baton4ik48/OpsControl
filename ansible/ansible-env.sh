# source ansible/ansible-env.sh перед ansible-playbook / ansible-inventory
#
# Задаётся через env, а не только ansible.cfg: env-переменные ANSIBLE_*
# имеют приоритет над ansible.cfg, поэтому подмена/удаление ansible.cfg
# в рабочей директории не сможет включить запись фактов/секретов на диск.

export ANSIBLE_CACHE_PLUGIN=memory
export ANSIBLE_RETRY_FILES_ENABLED=False
