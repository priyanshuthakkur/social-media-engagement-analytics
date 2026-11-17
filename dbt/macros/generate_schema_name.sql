{#
    Use the schema names set in dbt_project.yml as they are (staging, marts)
    instead of dbt's default of prefixing them with the target schema
    (main_staging, main_marts).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
