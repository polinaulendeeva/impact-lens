drop view if exists v_portfolio_exposure;
drop view if exists v_current_assessment;

create view v_current_assessment as
with latest_assessment as (
    select a.*,
           row_number() over (
               partition by a.company_id, a.theme_id
               order by a.created_at desc, a.id desc
           ) as rn
    from assessments a
    where a.prompt_version = (select max(prompt_version) from assessments)
),
latest_review as (
    select r.*,
           row_number() over (
               partition by r.assessment_id
               order by r.created_at desc, r.id desc
           ) as rn
    from reviews r
)
select a.id as assessment_id,
       a.company_id,
       a.theme_id,
       a.prompt_version,
       a.score as model_score,
       r.decision,
       r.reviewer,
       r.created_at as reviewed_at,
       case when r.decision = 'approve' then a.score
            when r.decision = 'edit' then r.edited_score
       end as final_score,
       case when r.decision is null then 'pending'
            when r.decision = 'reject' then 'rejected'
            else 'approved'
       end as status
from latest_assessment a
left join latest_review r on r.assessment_id = a.id and r.rn = 1
where a.rn = 1;

create view v_portfolio_exposure as
select h.portfolio,
       h.as_of,
       t.code as theme,
       round(coalesce(sum(h.weight * ca.final_score / 3.0)
             filter (where ca.status = 'approved'), 0), 1) as approved_exposure_pct,
       round(coalesce(sum(h.weight * ca.model_score / 3.0), 0), 1) as model_only_exposure_pct,
       round(coalesce(sum(h.weight)
             filter (where ca.status = 'approved'), 0), 1) as weight_reviewed_pct,
       round(coalesce(sum(h.weight)
             filter (where ca.status is distinct from 'approved'), 0), 1) as weight_not_reviewed_pct
from holdings h
cross join themes t
left join v_current_assessment ca
       on ca.company_id = h.company_id and ca.theme_id = t.id
group by h.portfolio, h.as_of, t.code;
